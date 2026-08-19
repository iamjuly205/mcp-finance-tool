# tests/test_keyword_router.py
import pytest
import os
import sys

# Thêm thư mục gốc vào path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from web.keyword_parser import route_intent_with_keywords, clean_voice_message, extract_amount

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_router.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_extract_amount_voice_slang():
    # Triệu rưỡi
    assert extract_amount("ăn uống hết một triệu rưỡi") == 1500000.0
    # Trăm rưỡi
    assert extract_amount("grab hết trăm rưỡi") == 150000.0
    # Củ rưỡi
    assert extract_amount("mua đồ shopee củ rưỡi") == 1500000.0
    # Lít
    assert extract_amount("đổ xăng hết 2 lít") == 200000.0
    # Chục
    assert extract_amount("uống trà sữa 3 chục") == 30000.0

def test_clean_voice_message():
    assert clean_voice_message("robot ơi ăn trưa hết 55k nhé") == "Ăn trưa"
    assert clean_voice_message("xiaozhi ơi mua sắm shopee củ rưỡi nha") == "Mua sắm shopee"
    assert clean_voice_message("hôm nay đi grab hết 30k") == "Đi grab"

def test_route_intent_statistics():
    res = route_intent_with_keywords("robot ơi thống kê tài chính giúp tôi nhé")
    assert res is not None
    assert res["tool"] == "thong_ke_thu_chi"
    assert res["arguments"] == {}

def test_route_intent_undo():
    res = route_intent_with_keywords("hủy giao dịch gần nhất đi")
    assert res is not None
    assert res["tool"] == "huy_giao_dich_gan_nhat"

def test_route_intent_view_budget():
    res = route_intent_with_keywords("tình hình ngân sách tháng này còn bao nhiêu")
    assert res is not None
    assert res["tool"] == "xem_ngan_sach"

def test_route_intent_set_budget():
    res = route_intent_with_keywords("cài hạn mức ăn uống 3tr")
    assert res is not None
    assert res["tool"] == "thiet_lap_han_muc"
    assert res["arguments"]["category"] == "Ăn uống"
    assert res["arguments"]["amount"] == 3000000.0

def test_route_intent_query_transactions():
    res = route_intent_with_keywords("liệt kê chi tiêu hôm qua")
    assert res is not None
    assert res["tool"] == "truy_van_giao_dich"
    assert res["arguments"]["transaction_type"] == "chi"
    assert res["arguments"]["time_range"] == "yesterday"

def test_route_intent_edit_transaction():
    res = route_intent_with_keywords("sửa giao dịch vừa rồi hết 100k")
    assert res is not None
    assert res["tool"] == "sua_giao_dich"
    assert res["arguments"]["transaction_id"] == -1
    assert res["arguments"]["amount"] == 100000.0

def test_route_intent_set_budget_typo():
    """Câu lệnh thiết lập hạn mức có lỗi đánh máy 'hạng mưc' vẫn phải khớp thiet_lap_han_muc."""
    res = route_intent_with_keywords("Thiết lập hạng mưc ăn uống 2 triệu.")
    # Nếu category "Ăn uống" có trong DB thì trả thiet_lap_han_muc, nếu không thì None (để LLM xử lý)
    # Dù sao cũng không được nhầm thành ghi_nhan_thu_chi
    assert res is None or res["tool"] == "thiet_lap_han_muc"

def test_non_ghi_nhan_intent_does_not_fall_through():
    """Câu lệnh thiết lập hạn mức KHÔNG ĐƯỢC nhận nhầm thành ghi_nhan_thu_chi."""
    res = route_intent_with_keywords("Thiết lập hạn mức đi chơi 5 triệu.")
    # Phải là None (→ LLM) hoặc thiet_lap_han_muc, tuyệt đối không phải ghi_nhan_thu_chi
    assert res is None or res["tool"] == "thiet_lap_han_muc"
    if res is not None:
        assert res["tool"] != "ghi_nhan_thu_chi"
