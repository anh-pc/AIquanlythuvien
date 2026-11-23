from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import Base, SessionLocal, engine
from app.models import Book, BorrowRecord, Category, Member

SEED_CATEGORIES = [
    {"name": "Công nghệ thông tin", "description": "Sách lập trình, kỹ thuật phần mềm, mạng máy tính và bảo mật."},
    {"name": "Khoa học dữ liệu & AI", "description": "Trí tuệ nhân tạo, học máy, phân tích dữ liệu lớn."},
    {"name": "Kinh tế & Quản trị", "description": "Quản trị kinh doanh, tài chính, quản lý dự án."},
    {"name": "Văn học Việt Nam", "description": "Tác phẩm văn học kinh điển và đương đại Việt Nam."},
    {"name": "Kỹ năng sống", "description": "Phát triển bản thân, tư duy phản biện, giao tiếp."},
    {"name": "Khoa học tự nhiên", "description": "Toán học, vật lý, hoá học và sinh học ứng dụng."},
    {"name": "Lịch sử & Địa lý", "description": "Lịch sử dân tộc, văn hoá và địa lý thế giới."},
    {"name": "Ngoại ngữ", "description": "Tài liệu học tiếng Anh, tiếng Nhật chuyên ngành."},
]

SEED_BOOKS = [
    {
        "title": "Lập trình Python cơ bản",
        "author": "Nguyễn Văn Minh",
        "isbn": "978-604-001-001",
        "publisher": "NXB Khoa học và Kỹ thuật",
        "published_year": 2024,
        "category_name": "Công nghệ thông tin",
        "total_copies": 10,
        "available_copies": 9,
    },
    {
        "title": "Lập trình Python nâng cao cho Web",
        "author": "Trần Quốc Bảo",
        "isbn": "978-604-001-002",
        "publisher": "NXB Thông tin và Truyền thông",
        "published_year": 2025,
        "category_name": "Công nghệ thông tin",
        "total_copies": 6,
        "available_copies": 6,
    },
    {
        "title": "Kiến trúc Hệ thống Phân tán",
        "author": "Lê Hoàng Nam",
        "isbn": "978-604-001-003",
        "publisher": "NXB Bách Khoa",
        "published_year": 2024,
        "category_name": "Công nghệ thông tin",
        "total_copies": 5,
        "available_copies": 5,
    },
    {
        "title": "Cấu trúc dữ liệu và Giải thuật",
        "author": "Phạm Gia Huy",
        "isbn": "978-604-001-004",
        "publisher": "NXB Đại học Quốc gia",
        "published_year": 2023,
        "category_name": "Công nghệ thông tin",
        "total_copies": 8,
        "available_copies": 8,
    },
    {
        "title": "Thiết kế Cơ sở dữ liệu Quan hệ",
        "author": "Đặng Thanh Tùng",
        "isbn": "978-604-001-005",
        "publisher": "NXB Khoa học và Kỹ thuật",
        "published_year": 2023,
        "category_name": "Công nghệ thông tin",
        "total_copies": 7,
        "available_copies": 7,
    },
    {
        "title": "Bảo mật Ứng dụng Web Thực chiến",
        "author": "Vũ Đình Khoa",
        "isbn": "978-604-001-006",
        "publisher": "NXB Thông tin và Truyền thông",
        "published_year": 2025,
        "category_name": "Công nghệ thông tin",
        "total_copies": 4,
        "available_copies": 4,
    },
    {
        "title": "DevOps và Tự động hoá Triển khai",
        "author": "Hoàng Minh Đức",
        "isbn": "978-604-001-007",
        "publisher": "NXB Bách Khoa",
        "published_year": 2025,
        "category_name": "Công nghệ thông tin",
        "total_copies": 5,
        "available_copies": 5,
    },
    {
        "title": "Nhập môn Trí tuệ nhân tạo và Học máy",
        "author": "Đỗ Quang Vinh",
        "isbn": "978-604-002-001",
        "publisher": "NXB Đại học Quốc gia",
        "published_year": 2024,
        "category_name": "Khoa học dữ liệu & AI",
        "total_copies": 6,
        "available_copies": 6,
    },
    {
        "title": "Phân tích dữ liệu với Python và Pandas",
        "author": "Ngô Thuỳ Linh",
        "isbn": "978-604-002-002",
        "publisher": "NXB Khoa học và Kỹ thuật",
        "published_year": 2024,
        "category_name": "Khoa học dữ liệu & AI",
        "total_copies": 7,
        "available_copies": 7,
    },
    {
        "title": "Học sâu và Mạng Nơ-ron Nhân tạo",
        "author": "Bùi Anh Tuấn",
        "isbn": "978-604-002-003",
        "publisher": "NXB Bách Khoa",
        "published_year": 2025,
        "category_name": "Khoa học dữ liệu & AI",
        "total_copies": 4,
        "available_copies": 4,
    },
    {
        "title": "Quản trị Dự án Phần mềm Agile",
        "author": "Lý Minh Châu",
        "isbn": "978-604-003-001",
        "publisher": "NXB Kinh tế",
        "published_year": 2023,
        "category_name": "Kinh tế & Quản trị",
        "total_copies": 5,
        "available_copies": 5,
    },
    {
        "title": "Kinh tế học Vi mô Ứng dụng",
        "author": "Phan Thanh Hà",
        "isbn": "978-604-003-002",
        "publisher": "NXB Kinh tế",
        "published_year": 2022,
        "category_name": "Kinh tế & Quản trị",
        "total_copies": 6,
        "available_copies": 6,
    },
    {
        "title": "Truyện Kiều - Khảo cứu và Chú giải",
        "author": "Nguyễn Du",
        "isbn": "978-604-004-001",
        "publisher": "NXB Văn học",
        "published_year": 2021,
        "category_name": "Văn học Việt Nam",
        "total_copies": 9,
        "available_copies": 9,
    },
    {
        "title": "Dế Mèn Phiêu Lưu Ký",
        "author": "Tô Hoài",
        "isbn": "978-604-004-002",
        "publisher": "NXB Kim Đồng",
        "published_year": 2022,
        "category_name": "Văn học Việt Nam",
        "total_copies": 12,
        "available_copies": 12,
    },
    {
        "title": "Tư duy Phản biện trong Kỷ nguyên Số",
        "author": "Trịnh Mai Hương",
        "isbn": "978-604-005-001",
        "publisher": "NXB Trẻ",
        "published_year": 2024,
        "category_name": "Kỹ năng sống",
        "total_copies": 8,
        "available_copies": 8,
    },
    {
        "title": "Tiếng Anh Chuyên ngành Công nghệ",
        "author": "Đinh Phương Thảo",
        "isbn": "978-604-008-001",
        "publisher": "NXB Giáo dục",
        "published_year": 2024,
        "category_name": "Ngoại ngữ",
        "total_copies": 6,
        "available_copies": 6,
    },
]

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
        "phone": "0912345678",
        "role": "member",
        "is_active": True,
    },
    {
        "member_code": "MEM002",
        "full_name": "Trần Thu Hà",
        "email": "ha.tt@student.edu.vn",
        "phone": "0987654321",
        "role": "member",
        "is_active": True,
    },
]


def seed_database(db: Session) -> None:
    Base.metadata.create_all(bind=engine)

    category_map: dict[str, Category] = {}
    for cat_data in SEED_CATEGORIES:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            existing = Category(**cat_data)
            db.add(existing)
            db.flush()
        category_map[existing.name] = existing

    book_map: dict[str, Book] = {}
    for book_data in SEED_BOOKS:
        existing_book = db.query(Book).filter(Book.isbn == book_data["isbn"]).first()
        if not existing_book:
            cat = category_map[book_data["category_name"]]
            existing_book = Book(
                title=book_data["title"],
                author=book_data["author"],
                isbn=book_data["isbn"],
                publisher=book_data["publisher"],
                published_year=book_data["published_year"],
                category_id=cat.id,
                total_copies=book_data["total_copies"],
                available_copies=book_data["available_copies"],
                is_deleted=False,
            )
            db.add(existing_book)
            db.flush()
        book_map[existing_book.isbn] = existing_book

    member_map: dict[str, Member] = {}
    for mem_data in SEED_MEMBERS:
        existing_mem = db.query(Member).filter(Member.member_code == mem_data["member_code"]).first()
        if not existing_mem:
            existing_mem = Member(**mem_data)
            db.add(existing_mem)
            db.flush()
        member_map[existing_mem.member_code] = existing_mem

    if db.query(BorrowRecord).count() == 0:
        now = datetime.now(timezone.utc)
        first_book = book_map["978-604-001-001"]
        first_member = member_map["MEM001"]
        db.add(
            BorrowRecord(
                book_id=first_book.id,
                member_id=first_member.id,
                borrow_date=now - timedelta(days=3),
                due_date=now + timedelta(days=11),
                status="borrowed",
                notes="Mượn phục vụ đồ án môn học",
            )
        )

    db.commit()


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed_database(session)
        print("Seed dữ liệu mẫu thành công: 8 thể loại, 16 đầu sách, 3 tài khoản, 1 phiếu mượn.")
    finally:
        session.close()
