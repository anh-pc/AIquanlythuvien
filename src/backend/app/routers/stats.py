from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import StatsResponse
from app.services.stats_service import get_overview_stats

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get("", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return get_overview_stats(db=db)
