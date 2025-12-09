"""
Admin API endpoints for book management and task monitoring.
"""
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from celery.result import AsyncResult

from app.core.deps import get_current_admin_user, get_db
from app.models.user import User
from app.models.book import Book
from app.models.word import Word
from app.models.celery_task import CeleryTask
from app.schemas.book import (
    BookCreate,
    BookUploadResponse,
    BookInfo,
    BookListResponse,
    BookUpdate,
    TaskInfo,
    TaskStatusResponse,
    WordInfo,
    WordListResponse,
    WordCreate,
    WordUpdate,
    EnrichmentRequest,
    EnrichmentResponse
)
from app.tasks.pdf_tasks import process_pdf_book
from app.tasks.ai_tasks import clean_ocr_data, batch_enrich_words
from app.tasks import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/books/upload", response_model=BookUploadResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Query(...),
    description: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    publisher: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a PDF book and start processing.

    Requires admin role.
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    try:
        # Create uploads directory
        upload_dir = Path("uploads") / "books"
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = upload_dir / f"{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Saved uploaded file: {file_path}")

        # Create book record
        new_book = Book(
            title=title,
            description=description,
            author=author,
            publisher=publisher,
            file_url=str(file_path),
            status="processing",
            total_pages=0,
            total_words=0
        )
        db.add(new_book)
        await db.commit()
        await db.refresh(new_book)

        # Start PDF processing task
        task = process_pdf_book.delay(new_book.id, str(file_path))

        logger.info(f"Started PDF processing task {task.id} for book {new_book.id}")

        return BookUploadResponse(
            book_id=new_book.id,
            title=new_book.title,
            file_url=new_book.file_url,
            status=new_book.status,
            task_id=task.id,
            message="Book uploaded successfully. Processing started."
        )

    except Exception as e:
        logger.error(f"Error uploading book: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload book: {str(e)}"
        )


@router.get("/books", response_model=BookListResponse)
async def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all books with pagination and filtering.

    Requires admin role.
    """
    # Build query
    query = select(Book)

    # Apply filters
    if status_filter:
        query = query.where(Book.status == status_filter)

    if search:
        query = query.where(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%"),
                Book.publisher.ilike(f"%{search}%")
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(Book)
    if status_filter:
        count_query = count_query.where(Book.status == status_filter)
    if search:
        count_query = count_query.where(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%"),
                Book.publisher.ilike(f"%{search}%")
            )
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get books
    query = query.offset(skip).limit(limit).order_by(Book.created_at.desc())
    result = await db.execute(query)
    books = result.scalars().all()

    return BookListResponse(
        total=total,
        books=[BookInfo.model_validate(book) for book in books]
    )


@router.get("/books/{book_id}", response_model=BookInfo)
async def get_book(
    book_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get book details by ID.

    Requires admin role.
    """
    stmt = select(Book).where(Book.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    return BookInfo.model_validate(book)


@router.put("/books/{book_id}", response_model=BookInfo)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update book information.

    Requires admin role.
    """
    stmt = select(Book).where(Book.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Update fields
    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)

    await db.commit()
    await db.refresh(book)

    return BookInfo.model_validate(book)


@router.delete("/books/{book_id}")
async def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a book and its associated words.

    Requires admin role.
    """
    stmt = select(Book).where(Book.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Delete associated words
    delete_words_stmt = select(Word).where(Word.book_id == book_id)
    words_result = await db.execute(delete_words_stmt)
    words = words_result.scalars().all()

    for word in words:
        await db.delete(word)

    # Delete book
    await db.delete(book)
    await db.commit()

    # Delete file
    try:
        file_path = Path(book.file_url)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to delete file {book.file_url}: {str(e)}")

    return {"message": "Book deleted successfully"}


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get task status and progress.

    Requires admin role.
    """
    # Get task from Celery
    task = AsyncResult(task_id, app=celery_app)

    # Get task info from database
    # (This would require a database query, but for now we'll use Celery's result)

    if task.state == "PENDING":
        response = {
            "task_id": task_id,
            "status": "pending",
            "progress": None,
            "result": None,
            "error_message": None
        }
    elif task.state == "PROGRESS":
        response = {
            "task_id": task_id,
            "status": "processing",
            "progress": task.info,
            "result": None,
            "error_message": None
        }
    elif task.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "status": "completed",
            "progress": None,
            "result": task.result,
            "error_message": None
        }
    elif task.state == "FAILURE":
        response = {
            "task_id": task_id,
            "status": "failed",
            "progress": None,
            "result": None,
            "error_message": str(task.info)
        }
    else:
        response = {
            "task_id": task_id,
            "status": task.state.lower(),
            "progress": None,
            "result": None,
            "error_message": None
        }

    return TaskStatusResponse(**response)


@router.get("/words", response_model=WordListResponse)
async def list_words(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    book_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List words with pagination and filtering.

    Requires admin role.
    """
    # Build query
    query = select(Word)

    # Apply filters
    if book_id:
        query = query.where(Word.book_id == book_id)

    if search:
        query = query.where(Word.spelling.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(Word)
    if book_id:
        count_query = count_query.where(Word.book_id == book_id)
    if search:
        count_query = count_query.where(Word.spelling.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get words
    query = query.offset(skip).limit(limit).order_by(Word.spelling)
    result = await db.execute(query)
    words = result.scalars().all()

    return WordListResponse(
        total=total,
        words=[WordInfo.model_validate(word) for word in words]
    )


@router.post("/words", response_model=WordInfo)
async def create_word(
    word_data: WordCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new word manually.

    Requires admin role.
    """
    # Check if word already exists
    stmt = select(Word).where(Word.spelling == word_data.spelling.lower())
    result = await db.execute(stmt)
    existing_word = result.scalar_one_or_none()

    if existing_word:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Word already exists"
        )

    # Create word
    new_word = Word(
        spelling=word_data.spelling.lower(),
        phonetic=word_data.phonetic,
        definitions=word_data.definitions,
        sentences=word_data.sentences or [],
        mnemonic=word_data.mnemonic,
        usage_notes=word_data.usage_notes,
        audio_url=word_data.audio_url,
        tags=word_data.tags or [],
        book_id=word_data.book_id
    )

    db.add(new_word)
    await db.commit()
    await db.refresh(new_word)

    return WordInfo.model_validate(new_word)


@router.put("/words/{word_id}", response_model=WordInfo)
async def update_word(
    word_id: int,
    word_update: WordUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update word information.

    Requires admin role.
    """
    stmt = select(Word).where(Word.id == word_id)
    result = await db.execute(stmt)
    word = result.scalar_one_or_none()

    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )

    # Update fields
    update_data = word_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(word, field, value)

    await db.commit()
    await db.refresh(word)

    return WordInfo.model_validate(word)


@router.delete("/words/{word_id}")
async def delete_word(
    word_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a word.

    Requires admin role.
    """
    stmt = select(Word).where(Word.id == word_id)
    result = await db.execute(stmt)
    word = result.scalar_one_or_none()

    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )

    await db.delete(word)
    await db.commit()

    return {"message": "Word deleted successfully"}


@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich_words(
    request: EnrichmentRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enrich words with AI-generated content.

    Requires admin role.
    """
    if request.word_ids:
        # Enrich specific words
        total_words = len(request.word_ids)
        task = batch_enrich_words.delay(None, request.word_ids)
    elif request.book_id:
        # Enrich all words in a book
        stmt = select(func.count()).select_from(Word).where(Word.book_id == request.book_id)
        result = await db.execute(stmt)
        total_words = result.scalar()

        task = batch_enrich_words.delay(request.book_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either word_ids or book_id must be provided"
        )

    return EnrichmentResponse(
        task_id=task.id,
        message="Enrichment task started",
        total_words=total_words
    )
