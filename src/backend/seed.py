import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.config import get_today
from app.database import Base, SessionLocal, engine, ensure_schema_and_migrations
from app.models import Book, BookCopy, BorrowRecord, Category, Loan, Member, Reader
from seed_data import (
    SEED_BOOKS,
    SEED_CATEGORIES,
    SEED_LOAN_TEMPLATES,
    SEED_READERS,
)

# Giữ hằng số tương thích nếu có script cũ import
SEED_MEMBERS = [
    {
        "member_code": "LIB001",
        "full_name": "Đặng Văn Anh (Thủ thư)",
        "email": "librarian@thuvien.edu.vn",
        "phone": "0905123456",
        "role": "librarian",
        "is_active": True,
    },
    {
        "member_code": "MEM001",
        "full_name": "Nguyễn Minh Tuấn",
        "email": "tuan.nm@student.edu.vn",
        "phone": "0912345601",
        "role": "member",
        "is_active": True,
    },
    {
        "member_code": "MEM002",
        "full_name": "Trần Thu Hà",
        "email": "ha.tt@student.edu.vn",
        "phone": "0912345602",
        "role": "member",
        "is_active": True,
    },
]


def sync_book_copy_counts(db: Session) -> None:
    """Đồng bộ total_copies và available_copies trên bảng books từ bảng book_copies."""
    books = db.query(Book).all()
    for b in books:
        copies = db.query(BookCopy).filter(BookCopy.book_id == b.id).all()
        if copies:
            b.total_copies = len(copies)
            b.available_copies = sum(1 for c in copies if c.status == "available")


def seed_database(db: Session, reset: bool = False) -> None:
    """
    Nạp dữ liệu mẫu cho hệ thống Quản lý Thư viện.
    - Nếu reset=True: xoá dữ liệu hiện có trong DB của ứng dụng trước khi nạp lại.
    - Nếu reset=False: bổ sung cộng thêm (idempotent), giữ nguyên dữ liệu đã có.
    """
    bind_engine = db.get_bind()
    ensure_schema_and_migrations(bind_engine)

    if reset:
        db.query(Loan).delete()
        db.query(BorrowRecord).delete()
        db.query(BookCopy).delete()
        db.query(Reader).delete()
        db.query(Member).delete()
        db.query(Book).delete()
        db.query(Category).delete()
        db.commit()

    # 1. Nạp 10 thể loại
    category_map: dict[str, Category] = {}
    for cat_data in SEED_CATEGORIES:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            existing = Category(**cat_data)
            db.add(existing)
            db.flush()
        category_map[existing.name] = existing

    # 2. Nạp 36 đầu sách và các bản sao (book_copies)
    book_list: list[Book] = []
    copy_map: dict[str, BookCopy] = {}

    for idx, book_data in enumerate(SEED_BOOKS, start=1):
        existing_book = db.query(Book).filter(Book.isbn == book_data["isbn"]).first()
        cat = category_map[book_data["category_name"]]
        copies_count = book_data.get("copies_count", 2)

        if not existing_book:
            existing_book = Book(
                title=book_data["title"],
                author=book_data["author"],
                isbn=book_data["isbn"],
                publisher=book_data["publisher"],
                published_year=book_data["published_year"],
                category_id=cat.id,
                total_copies=copies_count,
                available_copies=copies_count,
                is_deleted=False,
            )
            db.add(existing_book)
            db.flush()
        book_list.append(existing_book)

        # Tạo bản sao cho đầu sách nếu chưa có
        for copy_num in range(1, copies_count + 1):
            barcode = f"BS-{idx:03d}-{copy_num:02d}"
            existing_copy = db.query(BookCopy).filter(BookCopy.barcode == barcode).first()
            if not existing_copy:
                existing_copy = BookCopy(
                    book_id=existing_book.id,
                    barcode=barcode,
                    status="available",
                    note=f"Bản sao #{copy_num} của {existing_book.title}",
                )
                db.add(existing_copy)
                db.flush()
            copy_map[barcode] = existing_copy

    # Đảm bảo mọi sách cũ trong DB (nếu được thêm ngoài seed) đều có ít nhất 1 bản sao
    all_books_in_db = db.query(Book).all()
    for b in all_books_in_db:
        has_copy = db.query(BookCopy).filter(BookCopy.book_id == b.id).first()
        if not has_copy:
            auto_barcode = f"BS-AUTO-{b.id:04d}-01"
            c = BookCopy(
                book_id=b.id,
                barcode=auto_barcode,
                status="available",
                note="Bản sao tự động đồng bộ từ dữ liệu cũ",
            )
            db.add(c)
            db.flush()
            copy_map[auto_barcode] = c

    # 3. Nạp 12 độc giả (readers)
    reader_map: dict[str, Reader] = {}
    for r_data in SEED_READERS:
        existing_reader = db.query(Reader).filter(Reader.card_no == r_data["card_no"]).first()
        if not existing_reader:
            existing_reader = Reader(**r_data)
            db.add(existing_reader)
            db.flush()
        reader_map[existing_reader.card_no] = existing_reader

    # 4. Nạp 22 phiếu mượn (loans) với ngày tương đối theo get_today()
    today = get_today()
    if db.query(Loan).count() == 0:
        for tpl in SEED_LOAN_TEMPLATES:
            reader = reader_map.get(tpl["card_no"])
            copy_obj = copy_map.get(tpl["barcode"])
            if not reader or not copy_obj:
                continue

            borrowed_date = (today + timedelta(days=tpl["borrowed_offset"])).isoformat()
            due_date = (today + timedelta(days=tpl["due_offset"])).isoformat()
            returned_date = (
                (today + timedelta(days=tpl["returned_offset"])).isoformat()
                if tpl["returned_offset"] is not None
                else None
            )

            loan = Loan(
                reader_id=reader.id,
                copy_id=copy_obj.id,
                borrowed_at=borrowed_date,
                due_date=due_date,
                returned_at=returned_date,
                renew_count=tpl["renew_count"],
                return_condition=tpl["return_condition"],
                fine_amount=tpl["fine_amount"],
                note=tpl["note"],
            )
            db.add(loan)

            # Cập nhật trạng thái bản sao khớp với phiếu mượn
            if returned_date is None:
                copy_obj.status = "borrowed"
            else:
                if tpl["return_condition"] == "damaged":
                    copy_obj.status = "damaged"
                    copy_obj.note = "Bản sao bị hư hỏng khi trả"
                elif tpl["return_condition"] == "lost":
                    copy_obj.status = "lost"
                    copy_obj.note = "Bản sao bị thất lạc"
                else:
                    copy_obj.status = "available"

        db.flush()

    # 5. Giữ dữ liệu bảng members & borrow_records cũ để tương thích ngược
    member_map: dict[str, Member] = {}
    for mem_data in SEED_MEMBERS:
        existing_mem = db.query(Member).filter(Member.member_code == mem_data["member_code"]).first()
        if not existing_mem:
            existing_mem = Member(**mem_data)
            db.add(existing_mem)
            db.flush()
        member_map[existing_mem.member_code] = existing_mem

    if db.query(BorrowRecord).count() == 0 and book_list and "MEM001" in member_map:
        now = datetime.now(timezone.utc)
        db.add(
            BorrowRecord(
                book_id=book_list[0].id,
                member_id=member_map["MEM001"].id,
                borrow_date=now - timedelta(days=3),
                due_date=now + timedelta(days=11),
                status="borrowed",
                notes="Mượn phục vụ đồ án môn học",
            )
        )

    sync_book_copy_counts(db)
    db.commit()


def ensure_seeded_if_empty() -> None:
    """Tự động nạp dữ liệu mẫu khi DB trống lúc khởi động ứng dụng."""
    ensure_schema_and_migrations(engine)
    session = SessionLocal()
    try:
        has_books = session.query(Book).count() > 0
        has_readers = session.query(Reader).count() > 0
        if not has_books or not has_readers:
            seed_database(session, reset=False)
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nạp dữ liệu mẫu cho hệ thống AIquanlythuvien")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xoá dữ liệu cũ trong DB ứng dụng và nạp lại từ đầu",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        seed_database(session, reset=args.reset)
        cat_count = session.query(Category).count()
        book_count = session.query(Book).count()
        copy_count = session.query(BookCopy).count()
        reader_count = session.query(Reader).count()
        loan_count = session.query(Loan).count()
        print(
            f"Seed dữ liệu mẫu thành công (reset={args.reset}): "
            f"{cat_count} thể loại, {book_count} đầu sách, {copy_count} bản sao, "
            f"{reader_count} độc giả, {loan_count} phiếu mượn."
        )
    finally:
        session.close()
