from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    category_id: int
    category_name: str
    total_copies: int
    available_copies: int
    is_deleted: bool = False


class BookListResponse(BaseModel):
    items: List[BookResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BorrowCreateRequest(BaseModel):
    book_id: int
    member_id: int
    loan_days: int = Field(default=14, ge=1, le=60)
    notes: Optional[str] = None


class BorrowRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    book_title: str
    member_id: int
    member_name: str
    member_code: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    status: str
    notes: Optional[str] = None


class AIRecommendRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=300)


class AIRecommendResponse(BaseModel):
    provider: str
    model: str
    topic: str
    recommendation: str
    suggested_books: List[BookResponse]
