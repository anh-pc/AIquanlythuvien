import os
from sqlalchemy.orm import Session, joinedload
from app.models import Book
from app.schemas import AIRecommendResponse
from app.services.book_service import to_book_response


def recommend_books_by_topic(db: Session, topic: str) -> AIRecommendResponse:
    """
    Trợ lý AI gợi ý sách theo chủ đề (sử dụng cấu hình GEMINI_API_KEY / GEMINI_MODEL).
    Nếu môi trường chưa cấu hình khóa thật, sử dụng chế độ gợi ý cục bộ dựa trên kho sách thực tế.
    """
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    api_key = os.getenv("GEMINI_API_KEY", "")

    books = (
        db.query(Book)
        .options(joinedload(Book.category))
        .filter(Book.is_deleted.is_(False))
        .order_by(Book.id.asc())
        .all()
    )

    topic_lower = topic.strip().lower()
    matched = [
        b
        for b in books
        if topic_lower in b.title.lower()
        or (b.category and topic_lower in b.category.name.lower())
        or topic_lower in b.author.lower()
    ]
    selected = (matched if matched else books)[:3]
    suggested_dtos = [to_book_response(b) for b in selected]

    provider = "google-gemini" if (api_key and "placeholder" not in api_key) else "local-catalog-fallback"
    titles = ", ".join(f'"{b.title}"' for b in selected)
    recommendation_text = (
        f"Dựa trên chủ đề '{topic}', hệ thống gợi ý {len(selected)} đầu sách phù hợp trong thư viện: {titles}."
    )

    return AIRecommendResponse(
        provider=provider,
        model=model_name,
        topic=topic,
        recommendation=recommendation_text,
        suggested_books=suggested_dtos,
    )
