# tests/test_database.py
import pytest
import sqlite3
import os

# Import các hàm từ file database gốc của bạn
# Giả sử file database.py nằm ở thư mục gốc (ngoài tests)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

# Thiết lập Database Test (Dùng DB ảo trên RAM để không làm rác DB thật)
@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    # tmp_path là tính năng của Pytest, tạo ra thư mục rác an toàn
    # Chúng ta trỏ file DB vào thư mục rác này
    test_db_path = tmp_path / "test_finance.db"
    database.DB_FILE = str(test_db_path)
    
    # Khởi tạo bảng (Sẽ lưu vào file temp trên ổ cứng)
    database.init_db()
    
    yield
    # Test xong tự động dọn dẹp

def test_insert_giao_dich_thanh_cong():
    """Kiểm tra xem hàm insert có trả về đúng ID đầu tiên không"""
    new_id = database.insert_giao_dich("chi", 50000, "Ăn sáng", "Phở bò")
    assert new_id == 1

def test_get_summary_tinh_toan_chinh_xac():
    """Kiểm tra xem hàm thống kê có cộng trừ đúng tiền không"""
    database.insert_giao_dich("thu", 2000000, "Lương")
    database.insert_giao_dich("chi", 100000, "Cafe")
    database.insert_giao_dich("chi", 50000, "Gửi xe")
    
    summary = database.get_summary()
    assert summary["tong_thu"] == 2000000
    assert summary["tong_chi"] == 150000

def test_delete_last_transaction():
    """Kiểm tra chức năng Undo"""
    database.insert_giao_dich("chi", 50000, "Mua đồ")
    
    result = database.delete_last_transaction()
    assert result is True
    
    summary = database.get_summary()
    assert summary["tong_chi"] == 0

def test_query_giao_dich_today_filter():
    """Kiểm tra xem hàm query_giao_dich lọc theo ngày và danh mục đúng không"""
    database.insert_giao_dich("thu", 500000, "Lương tháng")
    database.insert_giao_dich("chi", 40000, "Ăn trưa")
    database.insert_giao_dich("chi", 15000, "Gửi xe")
    
    # 1. Lấy tất cả giao dịch hôm nay
    today_txs = database.query_giao_dich(time_range="today")
    assert len(today_txs) == 3
    
    # 2. Lọc theo category 'Ăn'
    food_txs = database.query_giao_dich(category="Ăn", time_range="today")
    assert len(food_txs) == 1
    assert food_txs[0]["category"] == "Ăn trưa"
    assert food_txs[0]["amount"] == 40000

    # 3. Lọc theo transaction_type 'thu'
    income_txs = database.query_giao_dich(transaction_type="thu", time_range="today")
    assert len(income_txs) == 1
    assert income_txs[0]["category"] == "Lương tháng"

def test_update_giao_dich_by_id_and_last():
    """Kiểm tra cập nhật giao dịch theo ID cụ thể và giao dịch gần nhất"""
    id1 = database.insert_giao_dich("chi", 50000, "Ăn sáng", "Bánh mì")
    id2 = database.insert_giao_dich("chi", 20000, "Trà đá", "Trà xanh")
    
    # 1. Cập nhật khoản trà đá (id2) sang 25000 và ghi chú mới
    assert database.update_giao_dich(transaction_id=id2, amount=25000, description="Trà đá Hà Nội") is True
    
    # Lấy lại kiểm tra
    txs = database.query_giao_dich(time_range="today")
    tx2 = [t for t in txs if t["id"] == id2][0]
    assert tx2["amount"] == 25000
    assert tx2["description"] == "Trà đá Hà Nội"
    
    # 2. Cập nhật giao dịch gần nhất (-1)
    assert database.update_giao_dich(transaction_id=-1, category="Nước ngọt", amount=15000) is True
    txs = database.query_giao_dich(time_range="today")
    tx_last = [t for t in txs if t["id"] == id2][0]
    assert tx_last["category"] == "Nước ngọt"
    assert tx_last["amount"] == 15000

def test_budget_database_operations():
    """Kiểm tra các hàm nghiệp vụ ngân sách ở tầng DB"""
    # 1. Đặt ngân sách
    database.set_ngan_sach("Ăn uống", 1000000)
    database.set_ngan_sach("Di chuyển", 300000)
    
    # 2. Lấy ngân sách cụ thể
    assert database.get_ngan_sach("Ăn uống") == 1000000
    assert database.get_ngan_sach("Di chuyển") == 300000
    assert database.get_ngan_sach("Mua sắm") is None
    
    # 3. Lấy tất cả ngân sách
    all_budgets = database.get_all_ngan_sach()
    assert len(all_budgets) == 2
    
    # 4. Đối sánh khớp danh mục tương đối
    match = database.find_matching_budget("Ăn sáng phở bò")
    assert match is not None
    assert match[0] == "Ăn uống"
    assert match[1] == 1000000
    
    # 5. Tính toán chi tiêu trong tháng khớp ngân sách
    database.insert_giao_dich("chi", 50000, "Ăn trưa")
    database.insert_giao_dich("chi", 30000, "Ăn tối")
    database.insert_giao_dich("chi", 20000, "Đổ xăng xe máy") # không khớp Ăn uống
    
    spent_eating = database.get_monthly_spending_for_budget_category("Ăn uống")
    assert spent_eating == 80000