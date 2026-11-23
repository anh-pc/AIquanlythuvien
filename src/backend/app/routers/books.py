from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_db
from app.schemas import (
    BookCopyCreateRequest,
    BookCopyListResponse,
    BookCopyResponse,
    BookCreateRequest,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from app.services.book_service import (
    create_book,
    create_book_copy,
    get_book_detail,
    list_book_copies,
    list_books,
    soft_delete_book,
    update_book,
)

router = APIRouter(prefix="/api/books", tags=["Books"])


@router.get("", response_model=BookListResponse)
def get_books(
    q: Optional[str] = Query(default=None, description="Từ khoá tìm kiếm theo tên sách hoặc tác giả"),
    keyword: Optional[str] = Query(default=None, description="Bí danh của q để tương thích ngược"),
    category_id: Optional[int] = Query(default=None, description="ID thể loại để lọc sách"),
    page: int = Query(default=1, ge=1, description="Trang hiện tại (>= 1)"),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
):
    search_term = q if q is not None else keyword
    return list_books(
        db=db,
        keyword=search_term,
        category_id=category_id,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=BookResponse, status_code=201)
def post_book(payload: BookCreateRequest, db: Session = Depends(get_db)):
    return create_book(db=db, payload=payload)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return get_book_detail(db=db, book_id=book_id)


@router.put("/{book_id}", response_model=BookResponse)
def put_book(book_id: int, payload: BookUpdateRequest, db: Session = Depends(get_db)):
    return update_book(db=db, book_id=book_id, payload=payload)


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    return soft_delete_book(db=db, book_id=book_id)


@router.get("/{book_id}/copies", response_model=BookCopyListResponse)
def get_copies_of_book(
    book_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return list_book_copies(db=db, book_id=book_id, page=page, page_size=page_size)


@router.post("/{book_id}/copies", response_model=BookCopyResponse, status_code=201)
def post_copy_of_book(
    book_id: int,
    payload: BookCopyCreateRequest,
    db: Session = Depends(get_db),
):
    return create_book_copy(db=db, book_id=book_id, payload=payload)
