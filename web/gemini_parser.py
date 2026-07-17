# web/gemini_parser.py
import os
import json
import logging
from dotenv import load_dotenv

# Tải biến môi trường từ file .env ở thư mục gốc của project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Khởi tạo genai nếu có API Key hợp lệ
genai_available = False
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        genai_available = True
        logging.info("Gemini API đã được cấu hình thành công.")
    except Exception as e:
        logging.error(f"Lỗi cấu hình Gemini API: {e}")
else:
    logging.warning("GEMINI_API_KEY không được tìm thấy hoặc chưa thay đổi giá trị mặc định. Sử dụng bộ phân tích cục bộ Regex làm dự phòng.")

def parse_with_gemini(message: str):
    """
    Sử dụng Gemini API để phân tích câu lệnh tự nhiên của người dùng (kể cả câu không dấu).
    Trả về dict chứa thông tin giao dịch trích xuất được hoặc None nếu phân tích thất bại/không có API key.
    """
    if not genai_available:
        return None
        
    # Danh sách danh mục chuẩn khớp với database
    categories_list = ["Ăn uống", "Di chuyển", "Học tập", "Mua sắm", "Lương", "Khác"]
    
    prompt = f"""
Bạn là robot trợ lý tài chính thông minh Xiaozhi. Nhiệm vụ của bạn là phân tích câu lệnh ghi chép tài chính của người dùng và trích xuất thành đối tượng JSON chuẩn.

### QUY TẮC PHÂN TÍCH QUAN TRỌNG:

1. **Xử lý tiếng Việt KHÔNG DẤU**:
   Hệ thống yêu cầu bạn xử lý hoàn hảo cả câu nói có dấu hoặc KHÔNG DẤU tiếng Việt (ví dụ: "an com 50k", "nhan luong 12tr", "di xe grab 30k"). Hãy khôi phục đúng dấu tiếng Việt cho trường "description".

2. **Xử lý câu lệnh KHÔNG RÕ THÔNG TIN / CHUNG CHUNG**:
   - Nếu câu lệnh chỉ có hành động chi và số tiền (ví dụ: "tieu 50k", "chi 100.000", "mat 200k", "-150k") -> Phân loại vào danh mục "Khác", đặt `transaction_type` = "chi" và `description` = "Chi tiêu chung".
   - Nếu câu lệnh chỉ có hành động thu và số tiền (ví dụ: "nhan 5tr", "co them 1tr", "duoc cho 200k", "+500k") -> Phân loại vào danh mục "Khác", đặt `transaction_type` = "thu" và `description` = "Thu nhập chung".
   - Nếu có mô tả hành động cụ thể nhưng không khớp danh mục chuẩn nào (ví dụ: "dong tien nha 3tr", "tra no 1tr", "cho vay 500k") -> Phân loại vào danh mục "Khác", giữ nguyên mô tả.

3. **Phân loại Danh mục (Bắt buộc trường "category" phải trả về chính xác 1 trong 6 chuỗi có dấu dưới đây)**:
   - "Ăn uống": Đồ ăn, thức uống, ăn sáng, cơm trưa, đi nhậu, trà sữa, cafe, mua bún phở, bánh mì... (Từ khóa không dấu: "an uong", "an sang", "com trua", "di nhau", "tra sua", "cafe", "pho", "banh mi", "com")
   - "Di chuyển": Grab, taxi, đổ xăng, sửa xe, xe bus, vé máy bay, vé tàu, đi lại... (Từ khóa không dấu: "di chuyen", "grab", "taxi", "do xang", "sua xe", "xe bus", "ve may bay", "ve tau", "di lai")
   - "Học tập": Mua sách vở, học phí, đóng học, mua khóa học, dụng cụ học tập... (Từ khóa không dấu: "hoc tap", "mua sach", "hoc phi", "dong hoc", "khoa hoc")
   - "Mua sắm": Quần áo, giày dép, mua đồ Shopee/Lazada/Tiki, mua sắm siêu thị, đồ gia dụng, mỹ phẩm... (Từ khóa không dấu: "mua sam", "quan ao", "giay dep", "shopee", "lazada", "tiki", "sieu thi", "do gia dung")
   - "Lương": Lương tháng, nhận lương, thưởng dự án, tiền công làm thêm... (Từ khóa không dấu: "luong", "nhan luong", "thuong", "tien cong")
   - "Khác": Tiền nhà, tiền điện nước, trả nợ, cho vay, từ thiện, rút tiền, gửi tiền, các giao dịch không rõ danh mục hoặc không khớp 5 danh mục trên.

4. **Số tiền (amount)**:
   Quy đổi tất cả các cách viết tắt về số thực tế:
   - "k", "nghìn", "ng", "ngan": nhân 1.000 (ví dụ: "50k" -> 50000, "20k000" -> 20000)
   - "tr", "triệu", "trieu": nhân 1.000.000 (ví dụ: "15tr" -> 15000000, "1tr5" hoặc "1.5tr" -> 15000000)
   - "chục": nhân 10.000 (ví dụ: "3 chục" -> 30000)

5. **Đánh giá tính hợp lệ (is_transaction)**:
   Chỉ chọn `true` nếu câu lệnh chứa số tiền hợp lệ và mô tả hành động ghi nhận tài chính. Nếu là câu chào hỏi, hỏi thông tin chung (ví dụ: "hello", "báo cáo tháng này", "xem hạn mức") -> Thiết lập `is_transaction` = false.

---

### CÁC VÍ DỤ MINH HỌA (FEW-SHOT EXAMPLES):

- **Input**: "an trua het 55k"
  **Output**: {{"is_transaction": true, "transaction_type": "chi", "amount": 55000, "category": "Ăn uống", "description": "Ăn trưa"}}

- **Input**: "tieu het 150k"
  **Output**: {{"is_transaction": true, "transaction_type": "chi", "amount": 150000, "category": "Khác", "description": "Chi tiêu chung"}}

- **Input**: "nhan luong 15tr"
  **Output**: {{"is_transaction": true, "transaction_type": "thu", "amount": 15000000, "category": "Lương", "description": "Nhận lương"}}

- **Input**: "co them 1.2tr"
  **Output**: {{"is_transaction": true, "transaction_type": "thu", "amount": 12000000, "category": "Khác", "description": "Thu nhập chung"}}

- **Input**: "di grab di lam het 30k"
  **Output**: {{"is_transaction": true, "transaction_type": "chi", "amount": 30000, "category": "Di chuyển", "description": "Đi Grab đi làm"}}

- **Input**: "dong tien nuoc 350k"
  **Output**: {{"is_transaction": true, "transaction_type": "chi", "amount": 350000, "category": "Khác", "description": "Đóng tiền nước"}}

- **Input**: "chào robot"
  **Output**: {{"is_transaction": false, "transaction_type": "chi", "amount": 0, "category": "Khác", "description": ""}}

---

Hãy phân tích câu lệnh sau và trả về một chuỗi JSON duy nhất, không có văn bản bao ngoài, không dùng block markdown ```json:
"{message}"
"""
    try:
        import google.generativeai as genai
        # Sử dụng model gemini-2.5-flash để phản hồi nhanh
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Enforce JSON output format
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        result_text = response.text.strip()
        data = json.loads(result_text)
        
        if data.get("is_transaction") and data.get("amount", 0) > 0:
            category = data.get("category", "Khác")
            # Bảo đảm danh mục nằm trong danh sách hợp lệ
            if category not in categories_list:
                category = "Khác"
                
            return {
                "transaction_type": data.get("transaction_type", "chi"),
                "amount": float(data.get("amount", 0)),
                "category": category,
                "description": data.get("description", message)
            }
        return None
    except Exception as e:
        logging.error(f"Lỗi gọi Gemini API để phân tích cú pháp: {e}")
        return None
