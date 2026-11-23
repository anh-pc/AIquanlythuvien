from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


def today_iso_default():
    from app.config import get_today_iso
    return get_today_iso()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    books = relationship("Book", back_populates="category")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(150), nullable=False, index=True)
    isbn = Column(String(30), nullable=True, unique=True)
    publisher = Column(String(150), nullable=True)
    published_year = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    category = relationship("Category", back_populates="books")
    copies = relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")
    borrow_records = relationship("BorrowRecord", back_populates="book")


class BookCopy(Base):
    __tablename__ = "book_copies"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'borrowed', 'damaged', 'lost')",
            name="ck_book_copies_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    barcode = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="available", index=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    book = relationship("Book", back_populates="copies")
    loans = relationship("Loan", back_populates="copy")


class Reader(Base):
    __tablename__ = "readers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    card_no = Column(String(30), nullable=False, unique=True, index=True)
    full_name = Column(String(150), nullable=False, index=True)
    phone = Column(String(25), nullable=True)
    email = Column(String(150), nullable=True, unique=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    loans = relationship("Loan", back_populates="reader")


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "return_condition IS NULL OR return_condition IN ('normal', 'damaged', 'lost')",
            name="ck_loans_return_condition",
        ),
        Index(
            "uq_loans_active_copy",
            "copy_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reader_id = Column(Integer, ForeignKey("readers.id"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("book_copies.id"), nullable=False, index=True)
    borrowed_at = Column(String(10), nullable=False, default=today_iso_default, index=True)
    due_date = Column(String(10), nullable=False, index=True)
    returned_at = Column(String(10), nullable=True, index=True)
    renew_count = Column(Integer, nullable=False, default=0)
    return_condition = Column(String(20), nullable=True)
    fine_amount = Column(Integer, nullable=False, default=0)
    note = Column(String(255), nullable=True)

    reader = relationship("Reader", back_populates="loans")
    copy = relationship("BookCopy", back_populates="loans")


# Giữ bảng Member & BorrowRecord từ phiên trước để tương thích ngược, không mất dữ liệu cũ
class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    member_code = Column(String(30), nullable=False, unique=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default="member")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    borrow_records = relationship("BorrowRecord", back_populates="member")


class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    borrow_date = Column(DateTime, nullable=False, default=utc_now)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="borrowed", index=True)
    notes = Column(String(255), nullable=True)

    book = relationship("Book", back_populates="borrow_records")
    member = relationship("Member", back_populates="borrow_records")
