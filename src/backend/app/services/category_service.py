from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Category
from app.schemas import CategoryListResponse, CategoryResponse
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword


def list_categories(
    db: Session,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> CategoryListResponse:
    """
    Lấy danh sách thể loại có hỗ trợ tìm kiếm từ backend theo quy tắc chuẩn hoá keyword
    và giới hạn số lượng kết quả trả về (limit hợp lý cho searchable dropdown).
    """
    query = db.query(Category)

    normalized_kw = normalize_keyword(keyword)
    if normalized_kw is not None:
        pattern = build_like_pattern(normalized_kw)
        query = query.filter(func.u_lower(Category.name).like(pattern, escape=ESCAPE_CHAR))

    total = query.count()
    categories = query.order_by(Category.name.asc()).limit(limit).all()

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
    )
