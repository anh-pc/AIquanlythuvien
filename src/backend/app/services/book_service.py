import math
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models import Book, Category
from app.schemas import BookListResponse, BookResponse
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword


def to_book_response(book: Book) -> BookResponse:
    category_name = book.category.name if book.category else ""
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        publisher=book.publisher,
        published_year=book.published_year,
        category_id=book.category_id,
        category_name=category_name,
        total_copies=book.total_copies,
        available_copies=book.available_copies,
        is_deleted=book.is_deleted,
    )


def list_books(
    db: Session,
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 5,
) -> BookListResponse:
    """
    Lấy danh sách sách có phân trang, hỗ trợ:
    - Tìm kiếm theo tên sách (keyword, đã chuẩn hoá & escape literal %, _)
    - Lọc theo thể loại (category_id)
    - Kết hợp AND giữa keyword và category_id
    - Luôn loại sách đã xoá mềm (is_deleted == False) ở cả danh sách và count
    """
    query = (
        db.query(Book)
        .options(joinedload(Book.category))
        .filter(Book.is_deleted.is_(False))
    )

    normalized_kw = normalize_keyword(keyword)
    if normalized_kw is not None:
        pattern = build_like_pattern(normalized_kw)
        query = query.filter(func.u_lower(Book.title).like(pattern, escape=ESCAPE_CHAR))

    if category_id is not None:
        query = query.filter(Book.category_id == category_id)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    books = (
        query.order_by(Book.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return BookListResponse(
        items=[to_book_response(b) for b in books],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def soft_delete_book(db: Session, book_id: int) -> bool:
    """Xoá mềm sách bằng cờ is_deleted = True."""
    book = db.query(Book).filter(Book.id == book_id, Book.is_deleted.is_(False)).first()
    if not book:
        return False
    book.is_deleted = True
    book.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True
