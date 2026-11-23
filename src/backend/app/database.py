import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from app.utils.search import unicode_casefold

load_dotenv()

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record):
    """
    1. Bật PRAGMA foreign_keys = ON cho mọi kết nối SQLite.
    2. Đăng ký hàm u_lower / u_casefold chuẩn Unicode NFC + casefold() cho SQLite.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        pass
    finally:
        cursor.close()

    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("u_lower", 1, unicode_casefold)
        dbapi_connection.create_function("u_casefold", 1, unicode_casefold)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_and_migrations(target_engine: Engine = engine) -> None:
    """
    Khởi tạo bảng và thực hiện migration cộng thêm (không làm mất dữ liệu cũ):
    - Đảm bảo partial unique index trên loans(copy_id) WHERE returned_at IS NULL (NV2).
    - Nếu DB cũ có dữ liệu ở bảng members hoặc books chưa có bản sao, tự động đồng bộ sang readers và book_copies.
    """
    Base.metadata.create_all(bind=target_engine)
    with target_engine.begin() as conn:
        # Tạo partial unique index đảm bảo 1 bản sao không bao giờ có 2 phiếu chưa trả (NV2)
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_loans_active_copy "
                "ON loans(copy_id) WHERE returned_at IS NULL;"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
