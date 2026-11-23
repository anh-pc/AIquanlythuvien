import math
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.config import (
    COPY_STATUS_LABELS,
    DEFAULT_PAGE_SIZE,
    MANUAL_ALLOWED_COPY_STATUSES,
)
from app.models import Book, BookCopy, Category, Loan
from app.schemas import (
    BookCopyCreateRequest,
    BookCopyListResponse,
    BookCopyResponse,
    BookCopyUpdateRequest,
    BookCreateRequest,
    BookListResponse,
    BookResponse,
    BookUpdateRequest,
)
from app.utils.search import ESCAPE_CHAR, build_like_pattern, normalize_keyword


def to_copy_response(copy_obj: BookCopy) -> BookCopyResponse:
    book_title = copy_obj.book.title if copy_obj.book else None
    book_author = copy_obj.book.author if copy_obj.book else None
    return BookCopyResponse(
        id=copy_obj.id,
        book_id=copy_obj.book_id,
        book_title=book_title,
        book_author=book_author,
        barcode=copy_obj.barcode,
        status=copy_obj.status,
        status_label=COPY_STATUS_LABELS.get(copy_obj.status, copy_obj.status),
        note=copy_obj.note,
    )


def to_book_response(book: Book, include_copies: bool = False) -> BookResponse:
    category_name = book.category.name if book.category else ""
    copies = list(book.copies) if book.copies is not None else []

    if copies:
        total_copies = len(copies)
        available_copies = sum(1 for c in copies if c.status == "available")
        borrowed_copies = sum(1 for c in copies if c.status == "borrowed")
        damaged_copies = sum(1 for c in copies if c.status == "damaged")
        lost_copies = sum(1 for c in copies if c.status == "lost")
    else:
        total_copies = book.total_copies
        available_copies = book.available_copies
        borrowed_copies = max(0, total_copies - available_copies)
        damaged_copies = 0
        lost_copies = 0

    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        publisher=book.publisher,
        published_year=book.published_year,
        publish_year=book.published_year,
        category_id=book.category_id,
        category_name=category_name,
        total_copies=total_copies,
        available_copies=available_copies,
        borrowed_copies=borrowed_copies,
        damaged_copies=damaged_copies,
        lost_copies=lost_copies,
        is_deleted=book.is_deleted,
        copies=[to_copy_response(c) for c in copies] if include_copies else None,
    )


def recalculate_book_copy_counters(db: Session, book: Book) -> None:
    copies = db.query(BookCopy).filter(BookCopy.book_id == book.id).all()
    book.total_copies = len(copies)
    book.available_copies = sum(1 for c in copies if c.status == "available")


def list_books(
    db: Session,
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> BookListResponse:
    """
    Lấy danh sách sách có phân trang, hỗ trợ:
    - AC1: Tìm kiếm theo tên sách HOẶC tên tác giả (OR giữa 2 trường), chuẩn hoá NFC + casefold + escape literal %, _
    - AC2: Lọc theo thể loại (category_id)
    - AC3: Kết hợp AND giữa keyword và category_id
    - AC4: total và total_pages tính sau khi áp dụng mọi filter
    - AC7: Luôn loại sách đã xoá mềm (is_deleted == False) ở mọi truy vấn và count
    """
    query = (
        db.query(Book)
        .options(joinedload(Book.category), joinedload(Book.copies))
        .filter(Book.is_deleted.is_(False))
    )

    normalized_kw = normalize_keyword(keyword)
    if normalized_kw is not None:
        pattern = build_like_pattern(normalized_kw)
        query = query.filter(
            or_(
                func.u_lower(Book.title).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Book.author).like(pattern, escape=ESCAPE_CHAR),
            )
        )

    if category_id is not None:
        query = query.filter(Book.category_id == category_id)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    books = (
        query.order_by(Book.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return BookListResponse(
        items=[to_book_response(b, include_copies=False) for b in books],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_book_detail(db: Session, book_id: int) -> BookResponse:
    book = (
        db.query(Book)
        .options(joinedload(Book.category), joinedload(Book.copies))
        .filter(Book.id == book_id, Book.is_deleted.is_(False))
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu sách.")
    return to_book_response(book, include_copies=True)


def create_book(db: Session, payload: BookCreateRequest) -> BookResponse:
    title_clean = normalize_keyword(payload.title)
    author_clean = normalize_keyword(payload.author)
    if not title_clean or not author_clean:
        raise HTTPException(status_code=400, detail="Tên sách và tác giả không được để trống.")

    category = db.query(Category).filter(Category.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Thể loại được chọn không tồn tại.")

    isbn_clean = normalize_keyword(payload.isbn) if payload.isbn else None
    if isbn_clean:
        dup_isbn = db.query(Book).filter(Book.isbn == isbn_clean).first()
        if dup_isbn:
            raise HTTPException(status_code=400, detail="Mã ISBN này đã tồn tại trên một đầu sách khác.")

    year_val = payload.published_year if payload.published_year is not None else payload.publish_year

    new_book = Book(
        title=title_clean,
        author=author_clean,
        category_id=category.id,
        isbn=isbn_clean,
        publisher=payload.publisher.strip() if payload.publisher else None,
        published_year=year_val,
        total_copies=payload.initial_copies,
        available_copies=payload.initial_copies,
        is_deleted=False,
    )
    db.add(new_book)
    db.flush()

    for idx in range(1, payload.initial_copies + 1):
        barcode = f"BS-{new_book.id:03d}-{idx:02d}"
        # Đảm bảo mã barcode không trùng
        suffix = idx
        while db.query(BookCopy).filter(BookCopy.barcode == barcode).first() is not None:
            suffix += 1
            barcode = f"BS-{new_book.id:03d}-{suffix:02d}"

        db.add(
            BookCopy(
                book_id=new_book.id,
                barcode=barcode,
                status="available",
                note=f"Bản sao #{idx}",
            )
        )

    db.commit()
    return get_book_detail(db, new_book.id)


def update_book(db: Session, book_id: int, payload: BookUpdateRequest) -> BookResponse:
    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.is_deleted.is_(False))
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu sách.")

    if payload.title is not None:
        title_clean = normalize_keyword(payload.title)
        if not title_clean:
            raise HTTPException(status_code=400, detail="Tên sách không được để trống.")
        book.title = title_clean

    if payload.author is not None:
        author_clean = normalize_keyword(payload.author)
        if not author_clean:
            raise HTTPException(status_code=400, detail="Tên tác giả không được để trống.")
        book.author = author_clean

    if payload.category_id is not None:
        cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Thể loại được chọn không tồn tại.")
        book.category_id = cat.id

    if payload.isbn is not None:
        isbn_clean = normalize_keyword(payload.isbn)
        if isbn_clean:
            dup = db.query(Book).filter(Book.id != book_id, Book.isbn == isbn_clean).first()
            if dup:
                raise HTTPException(status_code=400, detail="Mã ISBN này đã tồn tại trên một đầu sách khác.")
        book.isbn = isbn_clean

    if payload.publisher is not None:
        book.publisher = payload.publisher.strip() if payload.publisher.strip() else None

    year_val = payload.published_year if payload.published_year is not None else payload.publish_year
    if year_val is not None:
        book.published_year = year_val

    db.commit()
    return get_book_detail(db, book.id)


def soft_delete_book(db: Session, book_id: int) -> dict:
    """
    NV7: Đầu sách chỉ xoá mềm, chặn nếu có bản sao đang mượn.
    """
    book = (
        db.query(Book)
        .options(joinedload(Book.copies))
        .filter(Book.id == book_id, Book.is_deleted.is_(False))
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu sách.")

    # Kiểm tra có bản sao nào đang mượn hoặc có phiếu mượn chưa trả không
    copy_ids = [c.id for c in book.copies]
    has_borrowed_copy = any(c.status == "borrowed" for c in book.copies)
    has_active_loan = False
    if copy_ids:
        has_active_loan = (
            db.query(Loan)
            .filter(Loan.copy_id.in_(copy_ids), Loan.returned_at.is_(None))
            .first()
            is not None
        )

    if has_borrowed_copy or has_active_loan:
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá đầu sách đang có bản sao được độc giả mượn chưa trả.",
        )

    book.is_deleted = True
    book.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Đã xoá mềm đầu sách thành công.", "id": book_id}


def list_book_copies(
    db: Session,
    book_id: int,
    page: int = 1,
    page_size: int = 50,
) -> BookCopyListResponse:
    book = db.query(Book).filter(Book.id == book_id, Book.is_deleted.is_(False)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu sách.")

    query = (
        db.query(BookCopy)
        .options(joinedload(BookCopy.book))
        .filter(BookCopy.book_id == book_id)
    )
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    items = (
        query.order_by(BookCopy.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return BookCopyListResponse(
        items=[to_copy_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def search_copies(
    db: Session,
    q: Optional[str] = None,
    status: Optional[str] = None,
    book_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> BookCopyListResponse:
    """Tìm kiếm bản sao (phục vụ ô gõ tìm bản sao khi tạo phiếu mượn - UX2)."""
    query = (
        db.query(BookCopy)
        .join(Book, BookCopy.book_id == Book.id)
        .options(joinedload(BookCopy.book))
        .filter(Book.is_deleted.is_(False))
    )

    if status:
        query = query.filter(BookCopy.status == status)
    if book_id is not None:
        query = query.filter(BookCopy.book_id == book_id)

    norm_q = normalize_keyword(q)
    if norm_q is not None:
        pattern = build_like_pattern(norm_q)
        query = query.filter(
            or_(
                func.u_lower(BookCopy.barcode).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Book.title).like(pattern, escape=ESCAPE_CHAR),
                func.u_lower(Book.author).like(pattern, escape=ESCAPE_CHAR),
            )
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    items = (
        query.order_by(BookCopy.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return BookCopyListResponse(
        items=[to_copy_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_book_copy(
    db: Session,
    book_id: int,
    payload: BookCopyCreateRequest,
) -> BookCopyResponse:
    book = db.query(Book).filter(Book.id == book_id, Book.is_deleted.is_(False)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy đầu sách.")

    barcode_clean = normalize_keyword(payload.barcode)
    if not barcode_clean:
        raise HTTPException(status_code=400, detail="Mã bản sao (barcode) không được để trống.")

    if payload.status not in MANUAL_ALLOWED_COPY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái bản sao khi tạo mới chỉ được là 'Còn trong kho' (available), 'Hư hỏng' (damaged) hoặc 'Thất lạc' (lost).",
        )

    dup = db.query(BookCopy).filter(BookCopy.barcode == barcode_clean).first()
    if dup:
        raise HTTPException(status_code=400, detail="Mã bản sao (barcode) này đã tồn tại.")

    copy_obj = BookCopy(
        book_id=book_id,
        barcode=barcode_clean,
        status=payload.status,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(copy_obj)
    db.flush()
    recalculate_book_copy_counters(db, book)
    db.commit()
    db.refresh(copy_obj)
    return to_copy_response(copy_obj)


def update_book_copy(
    db: Session,
    copy_id: int,
    payload: BookCopyUpdateRequest,
) -> BookCopyResponse:
    """
    NV6: Không được đổi tay sang hoặc ra khỏi trạng thái 'Đang mượn' (borrowed).
    Chỉ đổi giữa 'available' / 'damaged' / 'lost' khi không có phiếu mượn chưa trả.
    """
    copy_obj = (
        db.query(BookCopy)
        .options(joinedload(BookCopy.book))
        .filter(BookCopy.id == copy_id)
        .first()
    )
    if not copy_obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao sách.")

    active_loan = (
        db.query(Loan)
        .filter(Loan.copy_id == copy_id, Loan.returned_at.is_(None))
        .first()
    )

    if payload.status is not None:
        if payload.status == "borrowed":
            raise HTTPException(
                status_code=400,
                detail="Không được đổi thủ công trạng thái bản sao sang 'Đang mượn'. Vui lòng tạo phiếu mượn.",
            )
        if copy_obj.status == "borrowed" or active_loan is not None:
            raise HTTPException(
                status_code=400,
                detail="Bản sao đang được độc giả mượn, không thể đổi trạng thái thủ công. Vui lòng thực hiện trả sách.",
            )
        if payload.status not in MANUAL_ALLOWED_COPY_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Trạng thái bản sao không hợp lệ.",
            )
        copy_obj.status = payload.status

    if payload.barcode is not None:
        bc_clean = normalize_keyword(payload.barcode)
        if not bc_clean:
            raise HTTPException(status_code=400, detail="Mã bản sao không được để trống.")
        dup = db.query(BookCopy).filter(BookCopy.id != copy_id, BookCopy.barcode == bc_clean).first()
        if dup:
            raise HTTPException(status_code=400, detail="Mã bản sao (barcode) này đã tồn tại.")
        copy_obj.barcode = bc_clean

    if payload.note is not None:
        copy_obj.note = payload.note.strip() if payload.note else None

    if copy_obj.book:
        recalculate_book_copy_counters(db, copy_obj.book)

    db.commit()
    db.refresh(copy_obj)
    return to_copy_response(copy_obj)
