from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import AIRecommendRequest, AIRecommendResponse
from app.services.ai_service import recommend_books_by_topic

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


@router.post("/recommend", response_model=AIRecommendResponse)
def recommend(payload: AIRecommendRequest, db: Session = Depends(get_db)):
    return recommend_books_by_topic(db=db, topic=payload.topic)
