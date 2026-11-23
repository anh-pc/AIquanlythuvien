from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models import Book, BorrowRecord, Member
from app.schemas import BorrowCreateRequest, BorrowRecordResponse


def _to_borrow_response(record: BorrowRecord) -> BorrowRecordResponse:
    return BorrowRecordResponse(
        id=record.id,
        book_id=record.book_id,
        book_title=record.book.title if record.book else "",
        member_id=record.member_id,
        member_name=record.member.full_name if record.member else "",
        member_code=record.member.member_code if record.member else "",
        borrow_date=record.borrow_date,
        due_date=record.due_date,
        return_date=record.return_date,
        status=record.status,
        notes=record.notes,
    )


def list_borrow_records(db: Session) -> List[BorrowRecordResponse]:
    records = (
        db.query(BorrowRecord)
        .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.member))
        .order_by(BorrowRecord.id.desc())
        .all()
    )
    return [_to_borrow_response(r) for r in records]


def borrow_book(db: Session, payload: BorrowCreateRequest) -> BorrowRecordResponse:
    """
    Quy trình mượn sách:
    1. Kiểm tra sách tồn tại, chưa bị xoá mềm (is_deleted == False) và còn bản khả dụng (available_copies > 0).
    2. Kiểm tra độc giả tồn tại và tài khoản đang hoạt động (is_active == True).
    3. Tạo phiếu mượn với hạn trả (due_date = borrow_date + loan_days).
    4. Giảm số bản khả dụng (available_copies -= 1).
    """
    book = db.query(Book).filter(Book.id == payload.book_id, Book.is_deleted.is_(False)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách hoặc sách đã ngừng phục vụ.")
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="Sách hiện đã hết bản có sẵn để mượn.")

    member = db.query(Member).filter(Member.id == payload.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy độc giả.")
    if not member.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản độc giả đang bị khoá.")

    now = datetime.now(timezone.utc)
    due = now + timedelta(days=payload.loan_days)

    record = BorrowRecord(
        book_id=book.id,
        member_id=member.id,
        borrow_date=now,
        due_date=due,
        status="borrowed",
        notes=payload.notes,
    )
    book.available_copies -= 1
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_borrow_response(record)


def return_book(db: Session, record_id: int) -> BorrowRecordResponse:
    """
    Quy trình trả sách:
    1. Kiểm tra phiếu mượn tồn tại và chưa trả.
    2. Ghi nhận thời điểm trả (return_date), kiểm tra quá hạn (return_date > due_date).
    3. Cập nhật trạng thái phiếu ('returned' hoặc 'overdue') và hoàn lại tồn kho (available_copies += 1).
    """
    record = (
        db.query(BorrowRecord)
        .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.member))
        .filter(BorrowRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu mượn.")
    if record.return_date is not None or record.status == "returned":
        raise HTTPException(status_code=400, detail="Phiếu mượn này đã được trả trước đó.")

    now = datetime.now(timezone.utc)
    due_date = record.due_date
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    record.return_date = now
    if now > due_date:
        record.status = "overdue"
        record.notes = (record.notes + " | " if record.notes else "") + "Trả sách quá hạn"
    else:
        record.status = "returned"

    if record.book and record.book.available_copies < record.book.total_copies:
        record.book.available_copies += 1

    db.commit()
    db.refresh(record)
    return _to_borrow_response(record)
