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
Bạn là robot trợ lý tài chính thông minh Xiaozhi. Nhiệm vụ của bạn là phân tích câu nói ghi chép giao dịch thu chi của người dùng và trích xuất thành đối tượng JSON chuẩn.
Hệ thống yêu cầu bạn xử lý hoàn hảo cả câu nói có dấu hoặc KHÔNG DẤU tiếng Việt (ví dụ: "an banh mi", "nhan luong", "di grab", "mua do shopee").

Hãy phân tích kỹ ngữ nghĩa của câu để tránh nhầm lẫn giữa THU (thu nhập, nhận tiền, cộng tiền, lương về...) và CHI (tiêu tiền, trả tiền, đi xe, mua đồ...).
Ví dụ về câu KHÔNG DẤU cần phân loại đúng:
- "chi 20k000 an banh mi" -> CHI, category: "Ăn uống", amount: 20000, description: "Ăn bánh mì"
- "an trua het 55k" -> CHI, category: "Ăn uống", amount: 55000, description: "Ăn trưa"
- "di xe grab het 30k" -> CHI, category: "Di chuyển", amount: 30000, description: "Đi xe Grab"
- "nhan luong 15tr" -> THU, category: "Lương", amount: 15000000, description: "Nhận lương"
- "mua do shopee 200k" -> CHI, category: "Mua sắm", amount: 200000, description: "Mua đồ Shopee"

Danh mục chi tiêu hợp lệ (Bắt buộc trường "category" trong JSON phải trả về chính xác một trong các chuỗi sau có đầy đủ dấu tiếng Việt):
- "Ăn uống": Đồ ăn, nước uống, cafe, bún phở, bánh mì, cơm trưa, đi nhậu, trà sữa... (không dấu: "an uong", "cafe", "banh mi", "pho", "com")
- "Di chuyển": Grab, taxi, xăng xe, vé máy bay, xe bus, bảo dưỡng xe, đi xe... (không dấu: "di chuyen", "xang", "xe", "grab", "taxi")
- "Học tập": Sách vở, học phí, khoá học, tài liệu giảng dạy, mua sách... (không dấu: "hoc tap", "hoc phi", "sach", "khoa hoc")
- "Mua sắm": Quần áo, mua sắm online, Shopee, Lazada, Tiki, đồ dùng gia đình... (không dấu: "mua sam", "shopee", "quan ao")
- "Lương": Lương tháng, thưởng dự án, làm thêm, nhận lương... (không dấu: "luong", "nhan luong", "thuong")
- "Khác": Tất cả các trường hợp không thuộc các nhóm trên (ví dụ: trả nợ, cho vay, từ thiện, tiền nhà, chuyển tiền...). (không dấu: "khac", "tra no", "cho vay")

Loại giao dịch (transaction_type):
- "thu": Nhận tiền, cộng tiền, kiếm được tiền, lương về.
- "chi": Tiêu tiền ra, thanh toán, mất tiền.

Số tiền (amount): Trích xuất và quy đổi về con số thực tế:
- k, nghìn, ng: nhân 1.000 (Ví dụ: "50k" -> 50000, "20k000" -> 20000)
- tr, triệu, trieu: nhân 1.000.000 (Ví dụ: "10tr" -> 10000000)
- đ, đồng, vnd: lấy số tương ứng.

Mô tả (description): Viết lại nội dung giao dịch bằng tiếng Việt CÓ DẤU chuẩn chỉnh, viết hoa chữ cái đầu (Ví dụ: "Đi grab đi làm" cho "di grab di lam").

Hãy trả về một chuỗi JSON duy nhất định dạng như sau, không có text bao ngoài, không dùng block markdown:
{{
  "is_transaction": true/false (chỉ chọn true nếu đây là câu lệnh ghi nhận một khoản tiền giao dịch cụ thể),
  "transaction_type": "thu" hoặc "chi",
  "amount": số tiền (float),
  "category": "Danh mục khớp chính xác từ danh sách trên (ví dụ: Ăn uống, Di chuyển, Học tập, Mua sắm, Lương, Khác)",
  "description": "Mô tả có dấu tiếng Việt"
}}

Câu lệnh cần phân tích: "{message}"
"""
    try:
        import google.generativeai as genai
        # Sử dụng model gemini-1.5-flash để phản hồi nhanh
        model = genai.GenerativeModel("gemini-1.5-flash")
        
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
