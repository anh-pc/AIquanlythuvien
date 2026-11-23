import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


def _unicode_lower(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value).lower()


@event.listens_for(Engine, "connect")
def register_sqlite_unicode_functions(dbapi_connection, connection_record):
    """Đăng ký hàm u_lower cho SQLite để hỗ trợ LOWER() chuẩn Unicode (tiếng Việt)."""
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("u_lower", 1, _unicode_lower)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
