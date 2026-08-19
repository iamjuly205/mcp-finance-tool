# tests/test_llm_budget_fallback.py
import pytest
import database
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_llm_fallback.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_is_category_match_refined():
    """Kiểm tra logic đối sánh refined mới"""
    # 1. Các trường hợp tiền/phí không được trùng nhau
    assert not database.is_category_match("Tiền học", "Tiền nhà")
    assert not database.is_category_match("Học phí", "Viện phí")
    
    # 2. Các trường hợp F&B phải khớp nhau
    assert database.is_category_match("Ăn uống", "Ăn trưa")
    assert database.is_category_match("Ăn uống", "Ăn sáng phở bò")
    
    # 3. Đi chơi vs Đi ăn không trùng nhau
    assert not database.is_category_match("Đi chơi", "Đi ăn")

@patch("database.fallback_matching_budget_to_llm")
def test_find_matching_budget_llm_fallback_and_learn(mock_fallback):
    # Thiết lập hạn mức ngân sách
    database.set_ngan_sach("Học tập", 500000)
    
    # Kiểm tra xem "Sách giáo khoa" lúc đầu có khớp cục bộ không (chắc chắn không khớp)
    assert not database.is_category_match("Học tập", "Sách giáo khoa")
    
    # Giả lập phản hồi từ LLM
    mock_fallback.return_value = "Học tập"
    
    # Thực hiện tìm kiếm hạn mức
    match = database.find_matching_budget("Sách giáo khoa")
    
    # Kiểm tra xem LLM fallback có khớp và tự động học không
    assert match is not None
    assert match[0] == "Học tập"
    assert match[1] == 500000
    
    # Xác nhận mock_fallback đã được gọi đúng tham số
    mock_fallback.assert_called_once_with("Sách giáo khoa", ["Học tập"])
    
    # Kiểm tra xem từ khóa học được đã được lưu vào cơ sở dữ liệu chưa
    mappings = database.get_keyword_mappings()
    sach_mapping = [m for m in mappings if m["keyword"] == "sách giáo khoa"]
    
    assert len(sach_mapping) == 1
    assert sach_mapping[0]["category"] == "Học tập"
    assert sach_mapping[0]["type"] == "chi"
