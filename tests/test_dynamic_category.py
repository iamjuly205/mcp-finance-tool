# tests/test_dynamic_category.py
import pytest
import database
from web.keyword_parser import detect_category, route_intent_with_keywords
from server import thiet_lap_han_muc, ghi_nhan_thu_chi

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_dynamic.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_dynamic_category_and_auto_keyword():
    # 1. Establish budget for a new dynamic category "Đi chơi"
    res = thiet_lap_han_muc(category="Đi chơi", amount=1000000.0)
    assert "Đã thiết lập hạn mức" in res
    assert "Đi chơi" in res
    
    # 2. Check that "đi chơi" is now in keywords_mapping and get_all_categories
    categories = database.get_all_categories()
    assert "Đi chơi" in categories
    
    from web.keyword_parser import detect_category
    detected = detect_category("đi chơi")
    assert detected == "Đi chơi"
    
    # 3. Record spending for "đi chơi"
    res_spend = ghi_nhan_thu_chi(transaction_type="chi", amount=1000000.0, category="Đi chơi", description="Đi chơi")
    assert "Đã ghi nhận khoản chi tiêu 1.000.000 đồng cho hạng mục Đi chơi." in res_spend
    # Should trigger budget check for "Đi chơi"
    assert "Đi chơi" in res_spend
