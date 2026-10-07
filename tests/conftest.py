import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
import backend.config as config

@pytest.fixture(scope="session")
def test_env():
    """Sets up an isolated test SQLite DB and storage directory."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_certificates.db")
    test_storage_dir = os.path.join(temp_dir, "test_storage")
    os.makedirs(test_storage_dir, exist_ok=True)

    # Patch config storage dir
    orig_storage = config.STORAGE_DIR
    config.STORAGE_DIR = config.Path(test_storage_dir)

    engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    import backend.services as services
    orig_services_session = services.SessionLocal
    services.SessionLocal = TestingSessionLocal

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Cleanup
    services.SessionLocal = orig_services_session
    app.dependency_overrides.clear()
    config.STORAGE_DIR = orig_storage
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def client(test_env):
    with TestClient(app) as test_client:
        yield test_client
