import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import InterviewEvent, InterviewRecord  # noqa: F401

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)


def override_get_session():
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def db_session() -> Session:
    with TestingSessionLocal() as session:
        yield session
