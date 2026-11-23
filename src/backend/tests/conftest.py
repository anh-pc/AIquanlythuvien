import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import set_today_override
from app.database import Base, configure_sqlite_connection, ensure_schema_and_migrations, get_db
from app.main import app
from seed import seed_database


@pytest.fixture()
def db_session():
    """
    Tạo SQLite in-memory riêng biệt cho mỗi test, bật foreign keys,
    đăng ký hàm Unicode NFC casefold (u_lower) và nạp dữ liệu mẫu từ seed_database.
    """
    set_today_override(None)
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):
        configure_sqlite_connection(dbapi_connection, connection_record)

    ensure_schema_and_migrations(test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    session = TestingSessionLocal()
    try:
        seed_database(session, reset=True)
        yield session
    finally:
        set_today_override(None)
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
