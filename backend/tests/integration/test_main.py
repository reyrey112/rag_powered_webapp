import pytest, os, sys
from starlette.testclient import TestClient

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, "../.."))

if backend_path not in sys.path:
    sys.path.append(backend_path)

from main import app

@pytest.fixture
def client():
    return TestClient(app)

# def test_base_route(client):
    """
    GIVEN a FastAPI application
    WHEN the '/' route is requested (GET)
    THEN check the response is valid
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"hello": "world"}