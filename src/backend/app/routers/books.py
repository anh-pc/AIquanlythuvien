from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import BookListResponse
from app.services.book_service import list_books, soft_delete_book

router = APIRouter(prefix="/api/books", tags=["Books"])


@router.get("", response_model=BookListResponse)
def get_books(
    keyword: Optional[str] = Query(default=None, description="Từ khoá tìm kiếm theo tên sách"),
    category_id: Optional[int] = Query(default=None, description="ID thể loại để lọc sách"),
    page: int = Query(default=1, ge=1, description="Trang hiện tại (>= 1)"),
    page_size: int = Query(default=5, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
):
    return list_books(
        db=db,
        keyword=keyword,
        category_id=category_id,
        page=page,
        page_size=page_size,
    )


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    deleted = soft_delete_book(db=db, book_id=book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách.")
    return {"message": "Đã xoá sách thành công.", "id": book_id}
