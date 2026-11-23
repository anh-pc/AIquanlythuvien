import math
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Category
from app.schemas import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword, unicode_casefold


def list_categories(
    db: Session,
    keyword: Optional[str] = None,
    limit: int = 20,
    page: int = 1,
) -> CategoryListResponse:
    """
    Lấy danh sách thể loại có hỗ trợ tìm kiếm từ backend theo quy tắc chuẩn hoá keyword
    và giới hạn số lượng kết quả trả về (limit hợp lý cho searchable combobox - AC10).
    """
    query = db.query(Category)

    normalized_kw = normalize_keyword(keyword)
    if normalized_kw is not None:
        pattern = build_like_pattern(normalized_kw)
        query = query.filter(func.u_lower(Category.name).like(pattern, escape=ESCAPE_CHAR))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 0
    offset = (page - 1) * limit
    categories = query.order_by(Category.name.asc()).offset(offset).limit(limit).all()

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
    )


def create_category(db: Session, payload: CategoryCreateRequest) -> CategoryResponse:
    name_clean = normalize_keyword(payload.name)
    if not name_clean:
        raise HTTPException(status_code=400, detail="Tên thể loại không được để trống.")

    folded = unicode_casefold(name_clean)
    existing = (
        db.query(Category)
        .filter(func.u_lower(Category.name) == folded)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Tên thể loại này đã tồn tại trong hệ thống.")

    cat = Category(
        name=name_clean,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryResponse.model_validate(cat)


def update_category(db: Session, category_id: int, payload: CategoryUpdateRequest) -> CategoryResponse:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Không tìm thấy thể loại.")

    name_clean = normalize_keyword(payload.name)
    if not name_clean:
        raise HTTPException(status_code=400, detail="Tên thể loại không được để trống.")

    folded = unicode_casefold(name_clean)
    duplicate = (
        db.query(Category)
        .filter(Category.id != category_id, func.u_lower(Category.name) == folded)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Tên thể loại này đã tồn tại trong hệ thống.")

    cat.name = name_clean
    cat.description = payload.description.strip() if payload.description else None
    db.commit()
    db.refresh(cat)
    return CategoryResponse.model_validate(cat)
