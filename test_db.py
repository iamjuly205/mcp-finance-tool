import sys
sys.stdout.reconfigure(encoding='utf-8')
from database import init_db, insert_giao_dich

print("--- Bắt đầu kiểm tra Database bằng Python ---")

# 1. Khởi tạo bảng
init_db()

# 2. Giả lập dữ liệu từ giọng nói Robot trích xuất ra
try:
    id_moi = insert_giao_dich(
        transaction_type="chi",
        amount=100000.0,
        category="Ăn uống",
        description="Hôm nay tôi mua đồ ăn"
    )
    print(f"🎉 Thành công! ID bản ghi mới là: {id_moi}")
except Exception as e:
    print(f"Thử nghiệm thất bại: {e}")