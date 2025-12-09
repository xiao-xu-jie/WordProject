"""
Celery tasks for PDF processing and OCR.
"""
import logging
from typing import List, Dict, Any
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.tasks import celery_app
from app.services.pdf_service import get_pdf_service
from app.services.ocr_service import get_ocr_service
from app.models.book import Book
from app.models.celery_task import CeleryTask, TaskStatus
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_pdf_book")
def process_pdf_book(self, book_id: int, pdf_path: str) -> Dict[str, Any]:
    """
    Process a PDF book: convert to images and extract text with OCR.

    Args:
        book_id: ID of the book in database
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with processing results:
            - book_id: Book ID
            - total_pages: Number of pages processed
            - total_words_extracted: Number of words extracted
            - ocr_results: List of OCR results per page
    """
    import asyncio

    task_id = self.request.id
    logger.info(f"Starting PDF processing task {task_id} for book {book_id}")

    try:
        # Update task status to PROCESSING
        asyncio.run(_update_task_status(task_id, TaskStatus.PROCESSING, book_id))

        # Initialize services
        pdf_service = get_pdf_service(dpi=300)
        ocr_service = get_ocr_service(lang="ch", use_gpu=False)

        # Get PDF info
        pdf_info = pdf_service.get_pdf_info(pdf_path)
        total_pages = pdf_info["total_pages"]

        logger.info(f"Processing PDF with {total_pages} pages")

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": total_pages, "status": "Converting PDF to images"}
        )

        # Convert PDF to images
        output_dir = Path("uploads") / "temp" / f"book_{book_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        image_paths = pdf_service.convert_pdf_to_images(
            pdf_path,
            output_dir=str(output_dir)
        )

        logger.info(f"Converted {len(image_paths)} pages to images")

        # Process each page with OCR
        ocr_results = []
        for i, image_path in enumerate(image_paths, 1):
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_pages,
                    "status": f"OCR processing page {i}/{total_pages}"
                }
            )

            # Extract text from image
            extracted_texts = ocr_service.extract_text_from_image(
                image_path,
                confidence_threshold=0.6
            )

            # Format for LLM
            formatted_text = ocr_service.format_for_llm(extracted_texts)

            ocr_results.append({
                "page_number": i,
                "image_path": image_path,
                "extracted_texts": extracted_texts,
                "formatted_text": formatted_text,
                "text_count": len(extracted_texts)
            })

            logger.info(f"Processed page {i}/{total_pages}: {len(extracted_texts)} text blocks")

        # Update book status
        asyncio.run(_update_book_status(book_id, "ocr_completed", total_pages))

        # Update task status to COMPLETED
        result = {
            "book_id": book_id,
            "total_pages": total_pages,
            "total_text_blocks": sum(r["text_count"] for r in ocr_results),
            "ocr_results": ocr_results
        }

        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            book_id,
            result=result
        ))

        logger.info(f"Completed PDF processing for book {book_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing PDF for book {book_id}: {str(e)}")

        # Update task status to FAILED
        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.FAILED,
            book_id,
            error_message=str(e)
        ))

        # Update book status to failed
        asyncio.run(_update_book_status(book_id, "failed", 0))

        raise


@celery_app.task(bind=True, name="process_single_page")
def process_single_page(
    self,
    book_id: int,
    page_number: int,
    image_path: str
) -> Dict[str, Any]:
    """
    Process a single page with OCR.

    Args:
        book_id: ID of the book
        page_number: Page number
        image_path: Path to the page image

    Returns:
        Dictionary with OCR results for the page
    """
    task_id = self.request.id
    logger.info(f"Processing page {page_number} of book {book_id}")

    try:
        # Initialize OCR service
        ocr_service = get_ocr_service(lang="ch", use_gpu=False)

        # Extract text from image
        extracted_texts = ocr_service.extract_text_from_image(
            image_path,
            confidence_threshold=0.6
        )

        # Format for LLM
        formatted_text = ocr_service.format_for_llm(extracted_texts)

        result = {
            "book_id": book_id,
            "page_number": page_number,
            "image_path": image_path,
            "extracted_texts": extracted_texts,
            "formatted_text": formatted_text,
            "text_count": len(extracted_texts)
        }

        logger.info(f"Completed OCR for page {page_number}: {len(extracted_texts)} text blocks")
        return result

    except Exception as e:
        logger.error(f"Error processing page {page_number} of book {book_id}: {str(e)}")
        raise


async def _update_task_status(
    task_id: str,
    status: TaskStatus,
    book_id: int,
    result: Dict[str, Any] = None,
    error_message: str = None
):
    """Update Celery task status in database."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if task exists
        stmt = select(CeleryTask).where(CeleryTask.task_id == task_id)
        result_obj = await session.execute(stmt)
        task = result_obj.scalar_one_or_none()

        if task:
            # Update existing task
            task.status = status
            if result:
                task.result = result
            if error_message:
                task.error_message = error_message
        else:
            # Create new task
            task = CeleryTask(
                task_id=task_id,
                task_name="process_pdf_book",
                status=status,
                book_id=book_id,
                result=result,
                error_message=error_message
            )
            session.add(task)

        await session.commit()

    await engine.dispose()


async def _update_book_status(book_id: int, status: str, total_pages: int):
    """Update book processing status in database."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()

        if book:
            book.status = status
            if total_pages > 0:
                book.total_pages = total_pages
            await session.commit()

    await engine.dispose()
