from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config import MAX_PAGE_SIZE
from app.database import get_db
from app.schemas import (
    BookCopyListResponse,
    BookCopyResponse,
    BookCopyUpdateRequest,
)
from app.services.book_service import search_copies, update_book_copy

router = APIRouter(prefix="/api/copies", tags=["Book Copies"])


@router.get("", response_model=BookCopyListResponse)
def get_copies(
    q: Optional[str] = Query(default=None, description="Tìm bản sao theo mã barcode hoặc tên sách"),
    status: Optional[str] = Query(default=None, description="Lọc theo trạng thái bản sao"),
    book_id: Optional[int] = Query(default=None, description="Lọc theo ID đầu sách"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return search_copies(
        db=db,
        q=q,
        status=status,
        book_id=book_id,
        page=page,
        page_size=page_size,
    )


@router.patch("/{copy_id}", response_model=BookCopyResponse)
def patch_copy(
    copy_id: int,
    payload: BookCopyUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_book_copy(db=db, copy_id=copy_id, payload=payload)
