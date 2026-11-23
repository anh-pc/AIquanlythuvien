import math
from datetime import date, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.config import (
    DEFAULT_PAGE_SIZE,
    FINE_PER_DAY,
    LOAN_DAYS,
    MAX_ACTIVE_LOANS,
    MAX_RENEWALS,
    RENEW_DAYS,
    VALID_RETURN_CONDITIONS,
    get_today,
    get_today_iso,
)
from app.models import Book, BookCopy, Loan, Reader
from app.schemas import (
    LoanCreateRequest,
    LoanListResponse,
    LoanResponse,
    LoanReturnRequest,
)
from app.services.book_service import recalculate_book_copy_counters
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword

LOAN_STATUS_LABELS = {
    "borrowed": "Đang mượn",
    "overdue": "Quá hạn",
    "returned": "Đã trả",
}


def derive_loan_status(loan: Loan, today: Optional[date] = None) -> Tuple[str, int, int]:
    """
    Suy ra trạng thái phiếu mượn (borrowed / overdue / returned), số ngày trễ và phí phạt:
    - Nếu returned_at != None -> 'returned'
    - Nếu returned_at == None và due_date < today -> 'overdue'
    - Ngược lại -> 'borrowed'
    """
    current_day = today or get_today()
    due = date.fromisoformat(str(loan.due_date)[:10])

    if loan.returned_at is not None:
        ret = date.fromisoformat(str(loan.returned_at)[:10])
        overdue_days = max(0, (ret - due).days)
        return "returned", overdue_days, loan.fine_amount

    if due < current_day:
        overdue_days = (current_day - due).days
        estimated_fine = overdue_days * FINE_PER_DAY
        return "overdue", overdue_days, estimated_fine

    return "borrowed", 0, 0


def to_loan_response(loan: Loan, today: Optional[date] = None) -> LoanResponse:
    status_code, overdue_days, est_fine = derive_loan_status(loan, today=today)
    copy_obj = loan.copy
    book_obj = copy_obj.book if copy_obj else None
    reader_obj = loan.reader

    return LoanResponse(
        id=loan.id,
        reader_id=loan.reader_id,
        reader_name=reader_obj.full_name if reader_obj else "",
        reader_card_no=reader_obj.card_no if reader_obj else "",
        copy_id=loan.copy_id,
        copy_barcode=copy_obj.barcode if copy_obj else "",
        book_id=book_obj.id if book_obj else 0,
        book_title=book_obj.title if book_obj else "",
        book_author=book_obj.author if book_obj else "",
        borrowed_at=str(loan.borrowed_at)[:10],
        due_date=str(loan.due_date)[:10],
        returned_at=str(loan.returned_at)[:10] if loan.returned_at else None,
        renew_count=loan.renew_count,
        return_condition=loan.return_condition,
        fine_amount=loan.fine_amount,
        status=status_code,
        status_label=LOAN_STATUS_LABELS.get(status_code, status_code),
        overdue_days=overdue_days,
        estimated_fine=est_fine,
        note=loan.note,
    )


def create_loan(db: Session, payload: LoanCreateRequest) -> LoanResponse:
    """
    NV1 & NV2: Mượn sách trong 1 transaction:
    - Độc giả tồn tại và đang hoạt động (is_active == True).
    - Bản sao tồn tại, đang 'Còn trong kho' (available), đầu sách chưa xoá (is_deleted == False).
    - Độc giả đang mượn < MAX_ACTIVE_LOANS (5).
    - Độc giả không có phiếu quá hạn (returned_at IS NULL và due_date < today).
    - Tạo phiếu với due_date = ngày mượn + LOAN_DAYS (14 ngày), chuyển bản sao -> 'borrowed'.
    """
    today = get_today()
    today_iso = today.isoformat()

    reader = db.query(Reader).filter(Reader.id == payload.reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")
    if not reader.is_active:
        raise HTTPException(
            status_code=400,
            detail="Thẻ độc giả hiện đang bị vô hiệu hoá, không thể mượn sách.",
        )

    copy_obj = (
        db.query(BookCopy)
        .options(joinedload(BookCopy.book))
        .filter(BookCopy.id == payload.copy_id)
        .first()
    )
    if not copy_obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao sách.")

    if not copy_obj.book or copy_obj.book.is_deleted:
        raise HTTPException(
            status_code=400,
            detail="Đầu sách của bản sao này đã bị xoá mềm, ngừng phục vụ mượn.",
        )

    # Kiểm tra phiếu chưa trả trên cùng bản sao (NV2)
    existing_copy_loan = (
        db.query(Loan)
        .filter(Loan.copy_id == copy_obj.id, Loan.returned_at.is_(None))
        .first()
    )
    if existing_copy_loan is not None or copy_obj.status == "borrowed":
        raise HTTPException(
            status_code=400,
            detail="Bản sao sách này đang được mượn chưa trả, không thể tạo phiếu mượn mới.",
        )

    if copy_obj.status != "available":
        status_vn = "Hư hỏng" if copy_obj.status == "damaged" else "Thất lạc"
        raise HTTPException(
            status_code=400,
            detail=f"Bản sao sách hiện ở tình trạng '{status_vn}', không thể cho mượn.",
        )

    # Kiểm tra các phiếu đang mượn của độc giả
    active_reader_loans = (
        db.query(Loan)
        .filter(Loan.reader_id == reader.id, Loan.returned_at.is_(None))
        .all()
    )
    if len(active_reader_loans) >= MAX_ACTIVE_LOANS:
        raise HTTPException(
            status_code=400,
            detail=f"Độc giả đang mượn tối đa {MAX_ACTIVE_LOANS} cuốn sách chưa trả, không thể mượn thêm.",
        )

    has_overdue = any(str(ln.due_date)[:10] < today_iso for ln in active_reader_loans)
    if has_overdue:
        raise HTTPException(
            status_code=400,
            detail="Độc giả đang có phiếu mượn quá hạn chưa trả, vui lòng trả sách quá hạn trước khi mượn mới.",
        )

    due_iso = (today + timedelta(days=LOAN_DAYS)).isoformat()

    new_loan = Loan(
        reader_id=reader.id,
        copy_id=copy_obj.id,
        borrowed_at=today_iso,
        due_date=due_iso,
        returned_at=None,
        renew_count=0,
        return_condition=None,
        fine_amount=0,
        note=payload.note.strip() if payload.note else None,
    )

    try:
        db.add(new_loan)
        copy_obj.status = "borrowed"
        recalculate_book_copy_counters(db, copy_obj.book)
        db.commit()
        db.refresh(new_loan)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bản sao sách này đã có phiếu mượn chưa trả trong hệ thống.",
        )

    return get_loan_by_id(db, new_loan.id)


def return_loan(db: Session, loan_id: int, payload: LoanReturnRequest) -> LoanResponse:
    """
    NV2 & NV3: Trả sách trong 1 transaction:
    - Phiếu phải chưa trả; nếu trả lần hai -> lỗi HTTP 409.
    - Nhận tình trạng normal / damaged / lost.
    - Ghi returned_at = hôm nay.
    - Bản sao -> 'available' (Còn trong kho) / 'damaged' (Hư hỏng) / 'lost' (Thất lạc).
    - Trả trễ -> fine_amount = ngày trễ * FINE_PER_DAY (1000).
    """
    loan = (
        db.query(Loan)
        .options(
            joinedload(Loan.reader),
            joinedload(Loan.copy).joinedload(BookCopy.book),
        )
        .filter(Loan.id == loan_id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu mượn.")

    if loan.returned_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Phiếu mượn này đã được trả trước đó, không thể trả lần hai.",
        )

    condition = (payload.return_condition or "normal").strip().lower()
    if condition not in VALID_RETURN_CONDITIONS:
        raise HTTPException(
            status_code=400,
            detail="Tình trạng trả sách không hợp lệ (chỉ chấp nhận: normal, damaged, lost).",
        )

    today = get_today()
    today_iso = today.isoformat()
    due = date.fromisoformat(str(loan.due_date)[:10])
    late_days = max(0, (today - due).days)
    fine = late_days * FINE_PER_DAY

    loan.returned_at = today_iso
    loan.return_condition = condition
    loan.fine_amount = fine
    if payload.note:
        loan.note = payload.note.strip()

    if loan.copy:
        if condition == "normal":
            loan.copy.status = "available"
        elif condition == "damaged":
            loan.copy.status = "damaged"
        elif condition == "lost":
            loan.copy.status = "lost"

        if loan.copy.book:
            recalculate_book_copy_counters(db, loan.copy.book)

    db.commit()
    db.refresh(loan)
    return to_loan_response(loan, today=today)


def renew_loan(db: Session, loan_id: int) -> LoanResponse:
    """
    NV4: Gia hạn phiếu mượn:
    - Phiếu phải chưa trả (returned_at IS NULL).
    - Phiếu chưa quá hạn (due_date >= hôm nay).
    - Số lần gia hạn renew_count < MAX_RENEWALS (2).
    - Thành công: due_date += RENEW_DAYS (7 ngày), renew_count += 1.
    """
    loan = (
        db.query(Loan)
        .options(
            joinedload(Loan.reader),
            joinedload(Loan.copy).joinedload(BookCopy.book),
        )
        .filter(Loan.id == loan_id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu mượn.")

    if loan.returned_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Không thể gia hạn phiếu mượn đã trả sách.",
        )

    today = get_today()
    today_iso = today.isoformat()
    if str(loan.due_date)[:10] < today_iso:
        raise HTTPException(
            status_code=400,
            detail="Phiếu mượn đã quá hạn, không thể thực hiện gia hạn.",
        )

    if loan.renew_count >= MAX_RENEWALS:
        raise HTTPException(
            status_code=400,
            detail=f"Phiếu mượn đã đạt giới hạn gia hạn tối đa ({MAX_RENEWALS} lần).",
        )

    current_due = date.fromisoformat(str(loan.due_date)[:10])
    new_due = (current_due + timedelta(days=RENEW_DAYS)).isoformat()
    loan.due_date = new_due
    loan.renew_count += 1

    db.commit()
    db.refresh(loan)
    return to_loan_response(loan, today=today)


def get_loan_by_id(db: Session, loan_id: int) -> LoanResponse:
    loan = (
        db.query(Loan)
        .options(
            joinedload(Loan.reader),
            joinedload(Loan.copy).joinedload(BookCopy.book),
        )
        .filter(Loan.id == loan_id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu mượn.")
    return to_loan_response(loan)


def list_loans(
    db: Session,
    status: Optional[str] = None,
    q: Optional[str] = None,
    reader_id: Optional[int] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> LoanListResponse:
    """
    Lấy danh sách phiếu mượn có phân trang, hỗ trợ:
    - Lọc theo trạng thái suy ra (borrowed | overdue | returned | active)
    - Lọc theo độc giả (reader_id - phục vụ NV8 lịch sử mượn của độc giả)
    - Tìm kiếm theo tên sách, mã bản sao, tên độc giả hoặc mã thẻ độc giả
    """
    today = get_today()
    today_iso = today.isoformat()

    query = (
        db.query(Loan)
        .join(Reader, Loan.reader_id == Reader.id)
        .join(BookCopy, Loan.copy_id == BookCopy.id)
        .join(Book, BookCopy.book_id == Book.id)
        .options(
            joinedload(Loan.reader),
            joinedload(Loan.copy).joinedload(BookCopy.book),
        )
    )

    if reader_id is not None:
        exists_reader = db.query(Reader).filter(Reader.id == reader_id).first()
        if not exists_reader:
            raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")
        query = query.filter(Loan.reader_id == reader_id)

    norm_status = normalize_keyword(status)
    if norm_status:
        st_lower = norm_status.lower()
        if st_lower == "borrowed":
            query = query.filter(Loan.returned_at.is_(None), Loan.due_date >= today_iso)
        elif st_lower == "overdue":
            query = query.filter(Loan.returned_at.is_(None), Loan.due_date < today_iso)
        elif st_lower == "returned":
            query = query.filter(Loan.returned_at.is_not(None))
        elif st_lower == "active":
            query = query.filter(Loan.returned_at.is_(None))

    norm_q = normalize_keyword(q)
    if norm_q is not None:
        pattern = build_like_pattern(norm_q)
        query = query.filter(
            or_(
                func.u_lower(Book.title).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(BookCopy.barcode).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Reader.full_name).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Reader.card_no).like(pattern, escape=ESCAPE_CHAR),
            )
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    loans = (
        query.order_by(Loan.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return LoanListResponse(
        items=[to_loan_response(ln, today=today) for ln in loans],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
