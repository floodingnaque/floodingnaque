"""Database fixtures - sessions, mocking, and integration helpers."""

import os
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Database Fixtures with Proper Cleanup
# ============================================================================


@pytest.fixture(scope="function")
def db_session_isolated(app, app_context):
    """
    Provide clean database session with rollback.

    Ensures each test starts with a clean database state.
    """
    try:
        from app.models.db import db

        db.create_all()

        yield db.session

        db.session.rollback()
        db.session.remove()
        db.drop_all()
    except ImportError:
        # If db module doesn't exist, yield None
        yield None


# ============================================================================
# Database Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database session for testing."""
    mock = MagicMock()
    mock.session = MagicMock()
    mock.session.add = MagicMock()
    mock.session.commit = MagicMock()
    mock.session.rollback = MagicMock()
    mock.session.query = MagicMock()
    mock.session.execute = MagicMock()
    mock.session.close = MagicMock()
    return mock


@pytest.fixture
def mock_db_session(mock_db):
    """Patch database session for testing."""
    with patch("app.models.db", mock_db):
        with patch("app.services.db", mock_db):
            yield mock_db


@pytest.fixture
def mock_sqlalchemy_engine():
    """Mock SQLAlchemy engine for connection testing."""
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
    engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    engine.execute = MagicMock()
    engine.dispose = MagicMock()
    return engine


@pytest.fixture
def sample_db_records():
    """Sample database records for testing."""
    return [
        {
            "id": 1,
            "timestamp": "2025-01-15T10:00:00Z",
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "prediction": 0,
            "flood_risk": "low",
        },
        {
            "id": 2,
            "timestamp": "2025-01-15T11:00:00Z",
            "temperature": 300.0,
            "humidity": 85.0,
            "precipitation": 25.0,
            "prediction": 1,
            "flood_risk": "high",
        },
    ]


# ============================================================================
# Database Integration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL (uses SQLite for testing)."""
    import tempfile

    temp_dir = tempfile.gettempdir()
    return f"sqlite:///{temp_dir}/test_floodingnaque.db"


@pytest.fixture(scope="function")
def db_session(app, test_database_url):
    """Create a database session for testing with automatic cleanup."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    # Use test database URL
    with app.app_context(), patch.dict(os.environ, {"DATABASE_URL": test_database_url}):
        engine = create_engine(test_database_url, echo=False)

        # Import models to create tables
        try:
            from app.models.db import Base

            Base.metadata.create_all(engine)
        except ImportError:
            pass

        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()

        yield session

        # Cleanup
        session.rollback()
        session.close()
        Session.remove()


@pytest.fixture
def mock_db_context():
    """Context manager for mocking database operations."""

    class DBContextMock:
        def __init__(self):
            self.session = MagicMock()
            self.queries = []

        def __enter__(self):
            return self.session

        def __exit__(self, *args):
            pass

        def record_query(self, query):
            self.queries.append(query)

    return DBContextMock()
