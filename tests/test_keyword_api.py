# tests/test_keyword_api.py
import pytest
import os
import sys
from fastapi.testclient import TestClient

# Thêm thư mục gốc vào path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from web.backend import app
import web.backend as backend

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_api_keyword.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_keywords_crud_endpoints():
    # 1. GET /api/keywords
    resp = client.get("/api/keywords")
    assert resp.status_code == 200
    initial_count = len(resp.json())
    assert initial_count > 0  # Should contain seeded keywords
    
    # 2. POST /api/keywords
    resp_post = client.post("/api/keywords", json={
        "keyword": "bún đậu",
        "category": "Ăn uống",
        "type": "chi"
    })
    assert resp_post.status_code == 200
    mapping_id = resp_post.json()["id"]
    assert mapping_id > 0
    
    # Verify it is added
    resp = client.get("/api/keywords")
    assert len(resp.json()) == initial_count + 1
    
    # 3. DELETE /api/keywords/{id}
    resp_del = client.delete(f"/api/keywords/{mapping_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["success"] is True
    
    # Verify it is deleted
    resp = client.get("/api/keywords")
    assert len(resp.json()) == initial_count

def test_chat_pipeline_prioritizes_keyword(monkeypatch):
    # Mock parse_with_gemini to raise an exception.
    # If it is called, the test should fail because keyword-first matching is expected to intercept.
    def mock_parse_with_gemini(message):
        raise AssertionError("Gemini parser was called, but keyword mapping should have intercepted!")
        
    monkeypatch.setattr(backend, "parse_with_gemini", mock_parse_with_gemini)
    
    # Test message with matching keyword: "uong tra sua het 35k" -> keyword "uống" -> "Ăn uống"
    resp = client.post("/api/chat", json={
        "message": "uong tra sua het 35k"
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "Ăn uống" in data["tts"]
    assert "35.000" in data["tts"]
    assert data["rpc_call"]["params"]["arguments"]["amount"] == 35000.0
