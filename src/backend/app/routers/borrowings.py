from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import BorrowCreateRequest, BorrowRecordResponse
from app.services.borrowing_service import borrow_book, list_borrow_records, return_book

router = APIRouter(prefix="/api/borrowings", tags=["Borrowings"])


@router.get("", response_model=List[BorrowRecordResponse])
def get_borrowings(db: Session = Depends(get_db)):
    return list_borrow_records(db)


@router.post("", response_model=BorrowRecordResponse)
def create_borrowing(payload: BorrowCreateRequest, db: Session = Depends(get_db)):
    return borrow_book(db, payload)


@router.post("/{record_id}/return", response_model=BorrowRecordResponse)
def return_borrowing(record_id: int, db: Session = Depends(get_db)):
    return return_book(db, record_id)
