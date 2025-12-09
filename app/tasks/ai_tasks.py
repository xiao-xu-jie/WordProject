"""
Celery tasks for AI-powered data cleaning and enrichment.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.tasks import celery_app
from app.services.ai_service import get_ai_service
from app.models.word import Word
from app.models.book import Book
from app.models.celery_task import CeleryTask, TaskStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="clean_ocr_data")
def clean_ocr_data(
    self,
    book_id: int,
    ocr_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Clean OCR data and extract structured vocabulary entries.

    Args:
        book_id: ID of the book
        ocr_results: List of OCR results from PDF processing

    Returns:
        Dictionary with cleaned word entries
    """
    import asyncio

    task_id = self.request.id
    logger.info(f"Starting data cleaning task {task_id} for book {book_id}")

    try:
        # Update task status
        asyncio.run(_update_task_status(task_id, TaskStatus.PROCESSING, book_id))

        # Initialize AI service
        ai_service = get_ai_service(provider="openai", model="gpt-4o-mini")

        # Process each page's OCR results
        all_words = []
        total_pages = len(ocr_results)

        for i, page_result in enumerate(ocr_results, 1):
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_pages,
                    "status": f"Cleaning page {i}/{total_pages}"
                }
            )

            formatted_text = page_result.get("formatted_text", "")
            if not formatted_text:
                continue

            # Clean OCR data with AI
            try:
                words = asyncio.run(ai_service.clean_ocr_data(
                    formatted_text,
                    context=f"Vocabulary book page {page_result['page_number']}"
                ))

                # Add page number to each word
                for word in words:
                    word["source_page"] = page_result["page_number"]

                all_words.extend(words)
                logger.info(f"Cleaned page {i}: extracted {len(words)} words")

            except Exception as e:
                logger.error(f"Error cleaning page {i}: {str(e)}")
                continue

        # Save words to database
        saved_count = asyncio.run(_save_words_to_db(book_id, all_words))

        # Update book status
        asyncio.run(_update_book_status(book_id, "ready", len(all_words)))

        result = {
            "book_id": book_id,
            "total_pages_processed": total_pages,
            "total_words_extracted": len(all_words),
            "total_words_saved": saved_count
        }

        # Update task status
        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            book_id,
            result=result
        ))

        logger.info(f"Completed data cleaning for book {book_id}: {saved_count} words saved")
        return result

    except Exception as e:
        logger.error(f"Error cleaning data for book {book_id}: {str(e)}")

        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.FAILED,
            book_id,
            error_message=str(e)
        ))

        raise


@celery_app.task(bind=True, name="enrich_word")
def enrich_word(self, word_id: int) -> Dict[str, Any]:
    """
    Enrich a single word with AI-generated content.

    Args:
        word_id: ID of the word to enrich

    Returns:
        Dictionary with enrichment results
    """
    import asyncio

    task_id = self.request.id
    logger.info(f"Starting word enrichment task {task_id} for word {word_id}")

    try:
        # Get word from database
        word_data = asyncio.run(_get_word_from_db(word_id))
        if not word_data:
            raise ValueError(f"Word {word_id} not found")

        # Initialize AI service
        ai_service = get_ai_service(provider="openai", model="gpt-4o-mini")

        # Enrich word
        enriched_data = asyncio.run(ai_service.enrich_word(
            word_data["spelling"],
            existing_data=word_data
        ))

        # Update word in database
        asyncio.run(_update_word_in_db(word_id, enriched_data))

        result = {
            "word_id": word_id,
            "spelling": word_data["spelling"],
            "enriched": True
        }

        logger.info(f"Completed enrichment for word {word_id}")
        return result

    except Exception as e:
        logger.error(f"Error enriching word {word_id}: {str(e)}")
        raise


@celery_app.task(bind=True, name="batch_enrich_words")
def batch_enrich_words(
    self,
    book_id: int,
    word_ids: List[int] = None
) -> Dict[str, Any]:
    """
    Enrich multiple words in batch.

    Args:
        book_id: ID of the book
        word_ids: List of word IDs to enrich (if None, enriches all words in book)

    Returns:
        Dictionary with batch enrichment results
    """
    import asyncio

    task_id = self.request.id
    logger.info(f"Starting batch enrichment task {task_id} for book {book_id}")

    try:
        # Update task status
        asyncio.run(_update_task_status(task_id, TaskStatus.PROCESSING, book_id))

        # Get words to enrich
        if word_ids is None:
            words = asyncio.run(_get_words_by_book(book_id))
        else:
            words = asyncio.run(_get_words_by_ids(word_ids))

        total_words = len(words)
        logger.info(f"Enriching {total_words} words")

        # Initialize AI service
        ai_service = get_ai_service(provider="openai", model="gpt-4o-mini")

        # Enrich words in batches
        enriched_count = 0
        batch_size = 5

        for i in range(0, total_words, batch_size):
            batch = words[i:i + batch_size]

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + len(batch),
                    "total": total_words,
                    "status": f"Enriching words {i + 1}-{i + len(batch)}/{total_words}"
                }
            )

            # Enrich batch
            enriched_batch = asyncio.run(ai_service.batch_enrich_words(batch, max_concurrent=5))

            # Update words in database
            for enriched_word in enriched_batch:
                word_id = enriched_word.get("id")
                if word_id:
                    asyncio.run(_update_word_in_db(word_id, enriched_word))
                    enriched_count += 1

            logger.info(f"Enriched batch {i // batch_size + 1}: {len(enriched_batch)} words")

        result = {
            "book_id": book_id,
            "total_words": total_words,
            "enriched_count": enriched_count
        }

        # Update task status
        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            book_id,
            result=result
        ))

        logger.info(f"Completed batch enrichment for book {book_id}: {enriched_count} words enriched")
        return result

    except Exception as e:
        logger.error(f"Error in batch enrichment for book {book_id}: {str(e)}")

        asyncio.run(_update_task_status(
            task_id,
            TaskStatus.FAILED,
            book_id,
            error_message=str(e)
        ))

        raise


# Helper functions

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
        stmt = select(CeleryTask).where(CeleryTask.task_id == task_id)
        result_obj = await session.execute(stmt)
        task = result_obj.scalar_one_or_none()

        if task:
            task.status = status
            if result:
                task.result = result
            if error_message:
                task.error_message = error_message
        else:
            task = CeleryTask(
                task_id=task_id,
                task_name="clean_ocr_data",
                status=status,
                book_id=book_id,
                result=result,
                error_message=error_message
            )
            session.add(task)

        await session.commit()

    await engine.dispose()


async def _save_words_to_db(book_id: int, words: List[Dict[str, Any]]) -> int:
    """Save words to database."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    saved_count = 0

    async with async_session() as session:
        for word_data in words:
            try:
                # Check if word already exists
                spelling = word_data.get("spelling", "").lower()
                stmt = select(Word).where(Word.spelling == spelling)
                result = await session.execute(stmt)
                existing_word = result.scalar_one_or_none()

                if existing_word:
                    # Update existing word
                    existing_word.phonetic = word_data.get("phonetic") or existing_word.phonetic
                    existing_word.definitions = word_data.get("definitions", [])
                    existing_word.sentences = word_data.get("sentences", [])
                    existing_word.tags = word_data.get("tags", [])
                else:
                    # Create new word
                    new_word = Word(
                        spelling=spelling,
                        phonetic=word_data.get("phonetic", ""),
                        definitions=word_data.get("definitions", []),
                        sentences=word_data.get("sentences", []),
                        tags=word_data.get("tags", []),
                        book_id=book_id
                    )
                    session.add(new_word)

                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving word {word_data.get('spelling')}: {str(e)}")
                continue

        await session.commit()

    await engine.dispose()
    return saved_count


async def _update_book_status(book_id: int, status: str, total_words: int):
    """Update book status in database."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()

        if book:
            book.status = status
            if total_words > 0:
                book.total_words = total_words
            await session.commit()

    await engine.dispose()


async def _get_word_from_db(word_id: int) -> Dict[str, Any]:
    """Get word data from database."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Word).where(Word.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            return None

        return {
            "id": word.id,
            "spelling": word.spelling,
            "phonetic": word.phonetic,
            "definitions": word.definitions,
            "sentences": word.sentences,
            "tags": word.tags
        }

    await engine.dispose()


async def _update_word_in_db(word_id: int, enriched_data: Dict[str, Any]):
    """Update word with enriched data."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Word).where(Word.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if word:
            if "sentences" in enriched_data:
                word.sentences = enriched_data["sentences"]
            if "mnemonic" in enriched_data:
                word.mnemonic = enriched_data["mnemonic"]
            if "usage_notes" in enriched_data:
                word.usage_notes = enriched_data.get("usage_notes")

            await session.commit()

    await engine.dispose()


async def _get_words_by_book(book_id: int) -> List[Dict[str, Any]]:
    """Get all words for a book."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Word).where(Word.book_id == book_id)
        result = await session.execute(stmt)
        words = result.scalars().all()

        return [
            {
                "id": w.id,
                "spelling": w.spelling,
                "phonetic": w.phonetic,
                "definitions": w.definitions,
                "sentences": w.sentences,
                "tags": w.tags
            }
            for w in words
        ]

    await engine.dispose()


async def _get_words_by_ids(word_ids: List[int]) -> List[Dict[str, Any]]:
    """Get words by IDs."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Word).where(Word.id.in_(word_ids))
        result = await session.execute(stmt)
        words = result.scalars().all()

        return [
            {
                "id": w.id,
                "spelling": w.spelling,
                "phonetic": w.phonetic,
                "definitions": w.definitions,
                "sentences": w.sentences,
                "tags": w.tags
            }
            for w in words
        ]

    await engine.dispose()
