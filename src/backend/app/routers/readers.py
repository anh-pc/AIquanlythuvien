from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_db
from app.schemas import (
    LoanListResponse,
    ReaderCreateRequest,
    ReaderListResponse,
    ReaderResponse,
    ReaderStatusUpdateRequest,
    ReaderUpdateRequest,
)
from app.services.loan_service import list_loans
from app.services.reader_service import (
    create_reader,
    get_reader_detail,
    list_readers,
    update_reader,
    update_reader_status,
)

router = APIRouter(prefix="/api/readers", tags=["Readers"])


@router.get("", response_model=ReaderListResponse)
def get_readers(
    q: Optional[str] = Query(default=None, description="Tìm độc giả theo tên, mã thẻ, SĐT, email"),
    is_active: Optional[bool] = Query(default=None, description="Lọc theo trạng thái hoạt động"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return list_readers(db=db, q=q, is_active=is_active, page=page, page_size=page_size)


@router.post("", response_model=ReaderResponse, status_code=201)
def post_reader(payload: ReaderCreateRequest, db: Session = Depends(get_db)):
    return create_reader(db=db, payload=payload)


@router.get("/{reader_id}", response_model=ReaderResponse)
def get_reader(reader_id: int, db: Session = Depends(get_db)):
    return get_reader_detail(db=db, reader_id=reader_id)


@router.put("/{reader_id}", response_model=ReaderResponse)
def put_reader(
    reader_id: int,
    payload: ReaderUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_reader(db=db, reader_id=reader_id, payload=payload)


@router.patch("/{reader_id}/status", response_model=ReaderResponse)
def patch_reader_status(
    reader_id: int,
    payload: ReaderStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_reader_status(db=db, reader_id=reader_id, payload=payload)


@router.get("/{reader_id}/loans", response_model=LoanListResponse)
def get_reader_loans(
    reader_id: int,
    status: Optional[str] = Query(default=None, description="borrowed | overdue | returned"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return list_loans(
        db=db,
        status=status,
        reader_id=reader_id,
        page=page,
        page_size=page_size,
    )
