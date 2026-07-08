# tests/test_server.py
import pytest
import os
import sys

# Đảm bảo import được thư mục gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import server

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    # Đổi file DB sang file tạm để tránh ghi đè lên dữ liệu thật
    test_db_path = tmp_path / "test_finance_server.db"
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield

def test_tool_ghi_nhan_thu_chi():
    # 1. Ghi nhận khoản chi tiêu
    res = server.ghi_nhan_thu_chi(transaction_type="chi", amount=150000, category="Ăn tối", description="Ăn lẩu")
    assert "Đã ghi nhận khoản chi tiêu 150.000 đồng cho hạng mục Ăn tối." in res
    
    # 2. Ghi nhận khoản thu nhập
    res2 = server.ghi_nhan_thu_chi(transaction_type="thu", amount=12000000, category="Lương")
    assert "Đã ghi nhận khoản thu nhập 12.000.000 đồng cho hạng mục Lương." in res2

def test_tool_thong_ke_thu_chi():
    server.ghi_nhan_thu_chi(transaction_type="thu", amount=50000, category="Nhặt được")
    server.ghi_nhan_thu_chi(transaction_type="chi", amount=20000, category="Trà sữa")
    
    res = server.thong_ke_thu_chi()
    assert "Tổng thu là 50.000 đồng" in res
    assert "tổng chi là 20.000 đồng" in res

def test_tool_huy_giao_dich_gan_nhat():
    # Ghi nhận xong hủy
    server.ghi_nhan_thu_chi(transaction_type="chi", amount=35000, category="Mua bút")
    res_undo = server.huy_giao_dich_gan_nhat()
    assert "Đã hủy giao dịch gần nhất thành công" in res_undo
    
    # Thống kê lại
    res_stat = server.thong_ke_thu_chi()
    assert "Tổng thu là 0 đồng" in res_stat
    assert "tổng chi là 0 đồng" in res_stat

def test_tool_truy_van_giao_dich():
    # Thêm vài giao dịch
    server.ghi_nhan_thu_chi(transaction_type="chi", amount=12000, category="Gửi xe")
    server.ghi_nhan_thu_chi(transaction_type="thu", amount=200000, category="Bán ve chai")
    
    # Lấy danh sách hôm nay
    res = server.truy_van_giao_dich(time_range="today")
    assert "Bán ve chai" in res
    assert "Gửi xe" in res
    assert "12.000đ" in res
    assert "200.000đ" in res

def test_tool_sua_giao_dich():
    # Thêm một giao dịch
    server.ghi_nhan_thu_chi(transaction_type="chi", amount=40000, category="Ăn sáng")
    
    # Sửa giao dịch gần nhất
    res_edit = server.sua_giao_dich(transaction_id=-1, amount=45000, description="Phở bò tái")
    assert "Đã cập nhật thành công giao dịch gần nhất" in res_edit
    
    # Truy vấn lại kiểm tra
    res_query = server.truy_van_giao_dich(time_range="today")
    assert "45.000đ" in res_query
    assert "Phở bò tái" in res_query

def test_tool_budgeting_and_warnings():
    # 1. Đặt ngân sách bằng tool
    res_set = server.thiet_lap_han_muc(category="Ăn uống", amount=100000)
    assert "Đã thiết lập hạn mức chi tiêu hàng tháng cho danh mục Ăn uống là 100.000 đồng" in res_set
    
    # 2. Chi tiêu dưới 80% (không có cảnh báo)
    res_spend1 = server.ghi_nhan_thu_chi(transaction_type="chi", amount=50000, category="Ăn trưa")
    assert "Đã ghi nhận khoản chi tiêu 50.000 đồng" in res_spend1
    assert "Cảnh báo" not in res_spend1
    
    # 3. Chi tiêu đạt >= 80% (có cảnh báo đạt 80% hoặc nhiều hơn)
    res_spend2 = server.ghi_nhan_thu_chi(transaction_type="chi", amount=30000, category="Ăn tối")
    assert "Đã ghi nhận khoản chi tiêu 30.000 đồng" in res_spend2
    # Tổng chi lúc này là 80.000đ / 100.000đ (80%)
    assert "Cảnh báo: Chi tiêu cho Ăn uống đã đạt 80% hạn mức tháng" in res_spend2
    
    # 4. Chi tiêu vượt hạn mức (> 100%)
    res_spend3 = server.ghi_nhan_thu_chi(transaction_type="chi", amount=30000, category="Ăn sáng")
    assert "Đã ghi nhận khoản chi tiêu 30.000 đồng" in res_spend3
    # Tổng chi lúc này là 110.000đ / 100.000đ (vượt hạn mức)
    assert "Cảnh báo: Bạn đã chi tiêu vượt hạn mức của danh mục Ăn uống" in res_spend3
    
    # 5. Xem báo cáo ngân sách bằng tool
    res_report = server.xem_ngan_sach()
    assert "Ăn uống: Đã tiêu 110.000đ / Hạn mức 100.000đ" in res_report
    assert "ĐÃ VƯỢT HẠN MỨC 10.000đ" in res_report
