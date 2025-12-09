"""
Pydantic schemas for book management.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BookCreate(BaseModel):
    """Schema for creating a new book."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    tags: Optional[List[str]] = []


class BookUploadResponse(BaseModel):
    """Schema for book upload response."""
    book_id: int
    title: str
    file_url: str
    status: str
    task_id: str
    message: str


class BookInfo(BaseModel):
    """Schema for book information."""
    id: int
    title: str
    description: Optional[str]
    author: Optional[str]
    publisher: Optional[str]
    file_url: str
    status: str
    total_pages: int
    total_words: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """Schema for book list response."""
    total: int
    books: List[BookInfo]


class BookUpdate(BaseModel):
    """Schema for updating book information."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskInfo(BaseModel):
    """Schema for task information."""
    task_id: str
    task_name: str
    status: str
    book_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """Schema for task status response."""
    task_id: str
    status: str
    progress: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]


class WordInfo(BaseModel):
    """Schema for word information."""
    id: int
    spelling: str
    phonetic: Optional[str]
    definitions: List[Dict[str, str]]
    sentences: Optional[List[Dict[str, str]]]
    mnemonic: Optional[str]
    usage_notes: Optional[str]
    audio_url: Optional[str]
    tags: List[str]
    book_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class WordListResponse(BaseModel):
    """Schema for word list response."""
    total: int
    words: List[WordInfo]


class WordCreate(BaseModel):
    """Schema for creating a new word."""
    spelling: str = Field(..., min_length=1, max_length=100)
    phonetic: Optional[str] = None
    definitions: List[Dict[str, str]] = Field(..., min_items=1)
    sentences: Optional[List[Dict[str, str]]] = []
    mnemonic: Optional[str] = None
    usage_notes: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[List[str]] = []
    book_id: Optional[int] = None


class WordUpdate(BaseModel):
    """Schema for updating word information."""
    spelling: Optional[str] = Field(None, min_length=1, max_length=100)
    phonetic: Optional[str] = None
    definitions: Optional[List[Dict[str, str]]] = None
    sentences: Optional[List[Dict[str, str]]] = None
    mnemonic: Optional[str] = None
    usage_notes: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[List[str]] = None


class EnrichmentRequest(BaseModel):
    """Schema for word enrichment request."""
    word_ids: Optional[List[int]] = None
    book_id: Optional[int] = None


class EnrichmentResponse(BaseModel):
    """Schema for enrichment response."""
    task_id: str
    message: str
    total_words: int
