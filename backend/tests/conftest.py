import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
