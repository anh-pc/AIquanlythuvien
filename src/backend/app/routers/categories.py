from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.services.category_service import (
    create_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
def get_categories(
    q: Optional[str] = Query(default=None, description="Từ khoá tìm kiếm theo tên thể loại"),
    keyword: Optional[str] = Query(default=None, description="Bí danh của q để tương thích ngược"),
    limit: int = Query(default=20, ge=1, le=100, description="Giới hạn số lượng thể loại trả về"),
    page: int = Query(default=1, ge=1, description="Trang hiện tại"),
    db: Session = Depends(get_db),
):
    search_term = q if q is not None else keyword
    return list_categories(db=db, keyword=search_term, limit=limit, page=page)


@router.post("", response_model=CategoryResponse, status_code=201)
def post_category(payload: CategoryCreateRequest, db: Session = Depends(get_db)):
    return create_category(db=db, payload=payload)


@router.put("/{category_id}", response_model=CategoryResponse)
def put_category(
    category_id: int,
    payload: CategoryUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_category(db=db, category_id=category_id, payload=payload)
