from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
# 1. Categories
# =====================================================================
class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


# =====================================================================
# 2. Book Copies (Bản sao sách)
# =====================================================================
class BookCopyCreateRequest(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)
    status: str = Field(default="available")
    note: Optional[str] = Field(default=None, max_length=255)


class BookCopyUpdateRequest(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=255)
    barcode: Optional[str] = Field(default=None, min_length=1, max_length=50)


class BookCopyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    barcode: str
    status: str
    status_label: str
    note: Optional[str] = None


class BookCopyListResponse(BaseModel):
    items: List[BookCopyResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =====================================================================
# 3. Books (Đầu sách)
# =====================================================================
class BookCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=150)
    category_id: int
    isbn: Optional[str] = Field(default=None, max_length=30)
    publisher: Optional[str] = Field(default=None, max_length=150)
    published_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    publish_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    initial_copies: int = Field(default=1, ge=0, le=50)


class BookUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    author: Optional[str] = Field(default=None, min_length=1, max_length=150)
    category_id: Optional[int] = None
    isbn: Optional[str] = Field(default=None, max_length=30)
    publisher: Optional[str] = Field(default=None, max_length=150)
    published_year: Optional[int] = Field(default=None, ge=1000, le=2100)
    publish_year: Optional[int] = Field(default=None, ge=1000, le=2100)


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    publish_year: Optional[int] = None
    category_id: int
    category_name: str
    total_copies: int
    available_copies: int
    borrowed_copies: int = 0
    damaged_copies: int = 0
    lost_copies: int = 0
    is_deleted: bool = False
    copies: Optional[List[BookCopyResponse]] = None


class BookListResponse(BaseModel):
    items: List[BookResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =====================================================================
# 4. Readers (Độc giả)
# =====================================================================
class ReaderCreateRequest(BaseModel):
    card_no: Optional[str] = Field(default=None, max_length=30)
    full_name: str = Field(..., min_length=1, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=25)
    email: Optional[str] = Field(default=None, max_length=150)
    address: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True


class ReaderUpdateRequest(BaseModel):
    card_no: Optional[str] = Field(default=None, min_length=1, max_length=30)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=25)
    email: Optional[str] = Field(default=None, max_length=150)
    address: Optional[str] = Field(default=None, max_length=255)


class ReaderStatusUpdateRequest(BaseModel):
    is_active: bool


class ReaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_no: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    active_loans_count: int = 0
    overdue_loans_count: int = 0


class ReaderListResponse(BaseModel):
    items: List[ReaderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =====================================================================
# 5. Loans (Phiếu mượn / trả / gia hạn)
# =====================================================================
class LoanCreateRequest(BaseModel):
    reader_id: int
    copy_id: int
    note: Optional[str] = Field(default=None, max_length=255)


class LoanReturnRequest(BaseModel):
    return_condition: str = Field(default="normal", description="normal | damaged | lost")
    note: Optional[str] = Field(default=None, max_length=255)


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reader_id: int
    reader_name: str
    reader_card_no: str
    copy_id: int
    copy_barcode: str
    book_id: int
    book_title: str
    book_author: str
    borrowed_at: str
    due_date: str
    returned_at: Optional[str] = None
    renew_count: int
    return_condition: Optional[str] = None
    fine_amount: int
    status: str
    status_label: str
    overdue_days: int = 0
    estimated_fine: int = 0
    note: Optional[str] = None


class LoanListResponse(BaseModel):
    items: List[LoanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =====================================================================
# 6. Stats (Thống kê tổng quan - NV9)
# =====================================================================
class TopBookStat(BaseModel):
    book_id: int
    title: str
    author: str
    category_name: str
    loan_count: int


class CopiesByStatusStat(BaseModel):
    available: int = 0
    borrowed: int = 0
    damaged: int = 0
    lost: int = 0
    total: int = 0


class StatsResponse(BaseModel):
    total_books: int
    copies_by_status: CopiesByStatusStat
    active_loans_count: int
    overdue_loans_count: int
    returned_loans_count: int
    active_readers_count: int
    total_readers_count: int
    top_borrowed_books: List[TopBookStat]


# =====================================================================
# 7. Legacy / AI Schemas (Giữ tương thích ngược)
# =====================================================================
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
