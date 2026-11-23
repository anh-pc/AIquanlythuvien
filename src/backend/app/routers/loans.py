from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_db
from app.schemas import (
    LoanCreateRequest,
    LoanListResponse,
    LoanResponse,
    LoanReturnRequest,
)
from app.services.loan_service import (
    create_loan,
    get_loan_by_id,
    list_loans,
    renew_loan,
    return_loan,
)

router = APIRouter(prefix="/api/loans", tags=["Loans"])


@router.get("", response_model=LoanListResponse)
def get_loans(
    status: Optional[str] = Query(default=None, description="borrowed | overdue | returned | active"),
    q: Optional[str] = Query(default=None, description="Tìm theo tên sách, mã bản sao, tên/mã độc giả"),
    reader_id: Optional[int] = Query(default=None, description="Lọc theo ID độc giả"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    return list_loans(
        db=db,
        status=status,
        q=q,
        reader_id=reader_id,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=LoanResponse, status_code=201)
def post_loan(payload: LoanCreateRequest, db: Session = Depends(get_db)):
    return create_loan(db=db, payload=payload)


@router.get("/{loan_id}", response_model=LoanResponse)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    return get_loan_by_id(db=db, loan_id=loan_id)


@router.post("/{loan_id}/return", response_model=LoanResponse)
def post_return_loan(
    loan_id: int,
    payload: Optional[LoanReturnRequest] = None,
    db: Session = Depends(get_db),
):
    req = payload or LoanReturnRequest(return_condition="normal")
    return return_loan(db=db, loan_id=loan_id, payload=req)


@router.post("/{loan_id}/renew", response_model=LoanResponse)
def post_renew_loan(loan_id: int, db: Session = Depends(get_db)):
    return renew_loan(db=db, loan_id=loan_id)
