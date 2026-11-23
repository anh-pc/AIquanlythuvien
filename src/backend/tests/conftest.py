import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, _unicode_lower
from app.main import app
from seed import seed_database


@pytest.fixture()
def db_session():
    """
    Tạo SQLite in-memory riêng biệt cho mỗi test, nạp dữ liệu mẫu từ seed_database
    để đảm bảo dữ liệu test độc lập, nhất quán và không phụ thuộc vào file DB bên ngoài.
    """
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _register_u_lower(dbapi_connection, connection_record):
        dbapi_connection.create_function("u_lower", 1, _unicode_lower)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
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
