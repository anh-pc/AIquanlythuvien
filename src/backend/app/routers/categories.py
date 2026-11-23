from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import CategoryListResponse
from app.services.category_service import list_categories

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
def get_categories(
    keyword: Optional[str] = Query(default=None, description="Từ khoá tìm kiếm theo tên thể loại"),
    limit: int = Query(default=20, ge=1, le=100, description="Giới hạn số lượng thể loại trả về"),
    db: Session = Depends(get_db),
):
    return list_categories(db=db, keyword=keyword, limit=limit)
