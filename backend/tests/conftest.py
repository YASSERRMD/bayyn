import sys
import importlib
import pytest
from unittest.mock import AsyncMock, patch

requires_asyncpg = pytest.mark.skipif(
    importlib.util.find_spec("asyncpg") is None,
    reason="asyncpg not installed; full API tests run in Docker with Python 3.12"
)

requires_python_312 = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Model annotations require Python 3.10+; run in Docker with Python 3.12"
)


@pytest.fixture
def client():
    asyncpg_spec = importlib.util.find_spec("asyncpg")
    if asyncpg_spec is None:
        pytest.skip("asyncpg not available")
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
