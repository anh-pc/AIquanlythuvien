import math
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.config import DEFAULT_PAGE_SIZE, get_today_iso
from app.models import Loan, Reader
from app.schemas import (
    ReaderCreateRequest,
    ReaderListResponse,
    ReaderResponse,
    ReaderStatusUpdateRequest,
    ReaderUpdateRequest,
)
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword


def to_reader_response(db: Session, reader: Reader) -> ReaderResponse:
    today_iso = get_today_iso()
    active_loans = (
        db.query(Loan)
        .filter(Loan.reader_id == reader.id, Loan.returned_at.is_(None))
        .all()
    )
    active_count = len(active_loans)
    overdue_count = sum(1 for ln in active_loans if ln.due_date < today_iso)

    return ReaderResponse(
        id=reader.id,
        card_no=reader.card_no,
        full_name=reader.full_name,
        phone=reader.phone,
        email=reader.email,
        address=reader.address,
        is_active=reader.is_active,
        active_loans_count=active_count,
        overdue_loans_count=overdue_count,
    )


def list_readers(
    db: Session,
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ReaderListResponse:
    query = db.query(Reader)

    if is_active is not None:
        query = query.filter(Reader.is_active.is_(is_active))

    norm_q = normalize_keyword(q)
    if norm_q is not None:
        pattern = build_like_pattern(norm_q)
        query = query.filter(
            or_(
                func.u_lower(Reader.full_name).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Reader.card_no).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(func.coalesce(Reader.phone, "")).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(func.coalesce(Reader.email, "")).like(pattern, escape=ESCAPE_CHAR),
            )
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    readers = (
        query.order_by(Reader.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ReaderListResponse(
        items=[to_reader_response(db, r) for r in readers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_reader_detail(db: Session, reader_id: int) -> ReaderResponse:
    reader = db.query(Reader).filter(Reader.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")
    return to_reader_response(db, reader)


def create_reader(db: Session, payload: ReaderCreateRequest) -> ReaderResponse:
    name_clean = normalize_keyword(payload.full_name)
    if not name_clean:
        raise HTTPException(status_code=400, detail="Họ tên độc giả không được để trống.")

    card_clean = normalize_keyword(payload.card_no) if payload.card_no else None
    if not card_clean:
        next_num = db.query(Reader).count() + 1
        card_clean = f"DG{next_num:03d}"
        while db.query(Reader).filter(Reader.card_no == card_clean).first() is not None:
            next_num += 1
            card_clean = f"DG{next_num:03d}"
    else:
        dup_card = db.query(Reader).filter(Reader.card_no == card_clean).first()
        if dup_card:
            raise HTTPException(status_code=400, detail="Mã thẻ độc giả này đã tồn tại.")

    email_clean = normalize_keyword(payload.email) if payload.email else None
    if email_clean:
        dup_email = db.query(Reader).filter(Reader.email == email_clean).first()
        if dup_email:
            raise HTTPException(status_code=400, detail="Email này đã được đăng ký cho một độc giả khác.")

    reader = Reader(
        card_no=card_clean,
        full_name=name_clean,
        phone=payload.phone.strip() if payload.phone else None,
        email=email_clean,
        address=payload.address.strip() if payload.address else None,
        is_active=payload.is_active,
    )
    db.add(reader)
    db.commit()
    db.refresh(reader)
    return to_reader_response(db, reader)


def update_reader(db: Session, reader_id: int, payload: ReaderUpdateRequest) -> ReaderResponse:
    reader = db.query(Reader).filter(Reader.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")

    if payload.full_name is not None:
        name_clean = normalize_keyword(payload.full_name)
        if not name_clean:
            raise HTTPException(status_code=400, detail="Họ tên độc giả không được để trống.")
        reader.full_name = name_clean

    if payload.card_no is not None:
        card_clean = normalize_keyword(payload.card_no)
        if not card_clean:
            raise HTTPException(status_code=400, detail="Mã thẻ độc giả không được để trống.")
        dup = db.query(Reader).filter(Reader.id != reader_id, Reader.card_no == card_clean).first()
        if dup:
            raise HTTPException(status_code=400, detail="Mã thẻ độc giả này đã tồn tại.")
        reader.card_no = card_clean

    if payload.email is not None:
        email_clean = normalize_keyword(payload.email)
        if email_clean:
            dup_em = db.query(Reader).filter(Reader.id != reader_id, Reader.email == email_clean).first()
            if dup_em:
                raise HTTPException(status_code=400, detail="Email này đã được sử dụng.")
        reader.email = email_clean

    if payload.phone is not None:
        reader.phone = payload.phone.strip() if payload.phone.strip() else None

    if payload.address is not None:
        reader.address = payload.address.strip() if payload.address.strip() else None

    db.commit()
    db.refresh(reader)
    return to_reader_response(db, reader)


def update_reader_status(
    db: Session,
    reader_id: int,
    payload: ReaderStatusUpdateRequest,
) -> ReaderResponse:
    """
    NV7: Độc giả không xoá cứng, chỉ vô hiệu hoá, chặn nếu còn sách chưa trả.
    Lịch sử mượn luôn được giữ.
    """
    reader = db.query(Reader).filter(Reader.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")

    if not payload.is_active:
        has_unreturned = (
            db.query(Loan)
            .filter(Loan.reader_id == reader_id, Loan.returned_at.is_(None))
            .first()
            is not None
        )
        if has_unreturned:
            raise HTTPException(
                status_code=400,
                detail="Không thể vô hiệu hoá độc giả đang có sách chưa trả.",
            )

    reader.is_active = payload.is_active
    db.commit()
    db.refresh(reader)
    return to_reader_response(db, reader)
