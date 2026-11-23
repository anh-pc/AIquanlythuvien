from sqlalchemy import func
from sqlalchemy.orm import Session
from app.config import get_today_iso
from app.models import Book, BookCopy, Category, Loan, Reader
from app.schemas import CopiesByStatusStat, StatsResponse, TopBookStat


def get_overview_stats(db: Session) -> StatsResponse:
    """
    NV9: Thống kê tổng quan:
    - Tổng đầu sách (chưa xoá mềm)
    - Số bản sao theo từng trạng thái (Còn trong kho, Đang mượn, Hư hỏng, Thất lạc)
    - Số phiếu đang mượn (chưa trả)
    - Số phiếu quá hạn (chưa trả và due_date < hôm nay)
    - Số độc giả hoạt động
    - Top 5 sách được mượn nhiều nhất
    """
    today_iso = get_today_iso()

    total_books = db.query(Book).filter(Book.is_deleted.is_(False)).count()

    # Đếm bản sao của các đầu sách chưa xoá theo trạng thái
    copy_rows = (
        db.query(BookCopy.status, func.count(BookCopy.id))
        .join(Book, BookCopy.book_id == Book.id)
        .filter(Book.is_deleted.is_(False))
        .group_by(BookCopy.status)
        .all()
    )
    status_counts = {row[0]: int(row[1]) for row in copy_rows}
    avail = status_counts.get("available", 0)
    borrowed = status_counts.get("borrowed", 0)
    damaged = status_counts.get("damaged", 0)
    lost = status_counts.get("lost", 0)

    copies_stat = CopiesByStatusStat(
        available=avail,
        borrowed=borrowed,
        damaged=damaged,
        lost=lost,
        total=avail + borrowed + damaged + lost,
    )

    active_loans_count = db.query(Loan).filter(Loan.returned_at.is_(None)).count()
    overdue_loans_count = (
        db.query(Loan)
        .filter(Loan.returned_at.is_(None), Loan.due_date < today_iso)
        .count()
    )
    returned_loans_count = db.query(Loan).filter(Loan.returned_at.is_not(None)).count()

    active_readers_count = db.query(Reader).filter(Reader.is_active.is_(True)).count()
    total_readers_count = db.query(Reader).count()

    # Top 5 sách được mượn nhiều nhất
    top_rows = (
        db.query(
            Book.id,
            Book.title,
            Book.author,
            Category.name.label("category_name"),
            func.count(Loan.id).label("loan_count"),
        )
        .join(Category, Book.category_id == Category.id)
        .outerjoin(BookCopy, BookCopy.book_id == Book.id)
        .outerjoin(Loan, Loan.copy_id == BookCopy.id)
        .filter(Book.is_deleted.is_(False))
        .group_by(Book.id, Book.title, Book.author, Category.name)
        .order_by(func.count(Loan.id).desc(), Book.id.asc())
        .limit(5)
        .all()
    )

    top_books = [
        TopBookStat(
            book_id=row.id,
            title=row.title,
            author=row.author,
            category_name=row.category_name,
            loan_count=int(row.loan_count),
        )
        for row in top_rows
    ]

    return StatsResponse(
        total_books=total_books,
        copies_by_status=copies_stat,
        active_loans_count=active_loans_count,
        overdue_loans_count=overdue_loans_count,
        returned_loans_count=returned_loans_count,
        active_readers_count=active_readers_count,
        total_readers_count=total_readers_count,
        top_borrowed_books=top_books,
    )
