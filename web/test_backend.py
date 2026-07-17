# web/test_backend.py
import pytest
import os
import sys
from fastapi.testclient import TestClient

# Thêm thư mục gốc vào path để python nhận diện package 'web' và import 'database'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from web.backend import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_web_finance.db"
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield

def test_api_summary_empty():
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json() == {"tong_thu": 0.0, "tong_chi": 0.0}

def test_api_create_and_query_transaction():
    # 1. Thêm giao dịch thu
    resp1 = client.post("/api/transactions", json={
        "transaction_type": "thu",
        "amount": 5000000.0,
        "category": "Lương",
        "description": "Lương tháng"
    })
    assert resp1.status_code == 200
    assert resp1.json()["success"] is True

    # 2. Thêm giao dịch chi
    resp2 = client.post("/api/transactions", json={
        "transaction_type": "chi",
        "amount": 20000.0,
        "category": "Ăn uống",
        "description": "Bánh mì"
    })
    assert resp2.status_code == 200

    # 3. Lấy summary
    resp_sum = client.get("/api/summary")
    assert resp_sum.json() == {"tong_thu": 5000000.0, "tong_chi": 20000.0}

    # 4. Lấy danh sách giao dịch
    resp_list = client.get("/api/transactions?time_range=this_month")
    assert len(resp_list.json()) == 2
    assert resp_list.json()[0]["amount"] == 20000.0

def test_api_budget_settings():
    # Đặt hạn mức
    resp = client.post("/api/budgets", json={
        "category": "Ăn uống",
        "amount": 100000.0
    })
    assert resp.status_code == 200
    
    # Thêm chi tiêu và kiểm tra cảnh báo
    resp_tx = client.post("/api/transactions", json={
        "transaction_type": "chi",
        "amount": 85000.0,
        "category": "Ăn uống",
        "description": "Lẩu"
    })
    assert resp_tx.status_code == 200
    assert "85%" in resp_tx.json()["warning"]

    # Xem ngân sách
    resp_budgets = client.get("/api/budgets")
    assert len(resp_budgets.json()) == 1
    assert resp_budgets.json()[0]["percentage"] == 85

def test_api_chat_simulation():
    resp = client.post("/api/chat", json={
        "message": "Hôm nay mua sách hết 120k"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "Mua sắm" in data["tts"] or "Khác" in data["tts"] or "120.000" in data["tts"]
    assert data["rpc_call"]["method"] == "tools/call"
