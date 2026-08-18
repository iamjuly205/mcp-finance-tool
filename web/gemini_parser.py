# web/gemini_parser.py
import os
import json
import logging
from dotenv import load_dotenv

# Tải biến môi trường từ file .env ở thư mục gốc của project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
    logging.warning("GEMINI_API_KEY không được tìm thấy. Gemini parser sẽ bị vô hiệu hóa.")

def parse_intent_with_gemini(message: str):
    """
    Sử dụng Gemini API để phân tích câu nói từ giọng nói (STT), phân loại ý định
    thành 1 trong 7 công cụ MCP và bóc tách các đối số tương ứng.
    """
    if not genai_available:
        return None
        
    categories_list = ["Ăn uống", "Di chuyển", "Học tập", "Mua sắm", "Lương", "Khác"]
    
    prompt = f"""
Bạn là robot trợ lý tài chính thông minh Xiaozhi. Nhiệm vụ của bạn là nhận dạng và phân tích câu nói của người dùng (từ giọng nói đã được chuyển thành văn bản STT) và dịch thành lệnh gọi công cụ MCP tương ứng dưới định dạng JSON.

### ĐẶC THÙ ĐẦU VÀO GIỌNG NÓI (STT):
1. Có thể chứa từ đệm vô nghĩa hoặc từ gọi robot (ví dụ: "robot ơi", "xiaozhi ơi", "nha", "nhé", "giùm tôi", "à", "ừm"). Hãy lọc bỏ chúng khỏi tham số `description`.
2. Có thể bị mất dấu tiếng Việt hoặc sai dấu nhẹ (ví dụ: "an trua het 55k", "chuc cu ruoi"). Hãy phục hồi đúng tiếng Việt có dấu.
3. Số tiền có thể được nói bằng chữ hoàn toàn (ví dụ: "hai triệu rưỡi" -> 2500000, "năm mươi lăm nghìn" -> 55000, "trăm rưỡi" -> 150000, "một củ" -> 1000000, "ba lít" -> 300000). Hãy quy đổi chính xác thành số thực tế.

---

### DANH SÁCH 7 CÔNG CỤ (MCP TOOLS) VÀ THAM SỐ:

1. **`thong_ke_thu_chi`**: Khi người dùng muốn xem báo cáo, thống kê, tổng quan tình hình tài chính thu nhập/chi tiêu.
   - Arguments: `{{}}` (không có tham số).

2. **`huy_giao_dich_gan_nhat`**: Khi người dùng muốn hủy, xóa, hoặc hoàn tác giao dịch vừa nhập sai.
   - Arguments: `{{}}` (không có tham số).

3. **`xem_ngan_sach`**: Khi người dùng muốn xem báo cáo ngân sách, hạn mức chi tiêu còn lại của các danh mục.
   - Arguments: `{{}}` (không có tham số).

4. **`thiet_lap_han_muc`**: Khi người dùng muốn cài đặt/cập nhật hạn mức chi tiêu hàng tháng cho một danh mục.
   - Arguments:
     * `category` (Bắt buộc): Một trong các danh mục chuẩn: {categories_list}.
     * `amount` (Bắt buộc): Số tiền hạn mức (số dương).

5. **`sua_giao_dich`**: Khi người dùng muốn sửa đổi thông tin của một giao dịch đã lưu.
   - Arguments:
     * `transaction_id` (Bắt buộc): ID giao dịch cần sửa. Nếu người dùng nói sửa giao dịch "vừa rồi", "gần nhất", "vừa nhập" -> điền `-1`.
     * `transaction_type` (Tùy chọn): "thu" hoặc "chi".
     * `amount` (Tùy chọn): Số tiền mới.
     * `category` (Tùy chọn): Danh mục mới trong {categories_list}.
     * `description` (Tùy chọn): Ghi chú mới.

6. **`truy_van_giao_dich`**: Khi người dùng muốn liệt kê, xem danh sách giao dịch cụ thể theo bộ lọc.
   - Arguments:
     * `transaction_type` (Tùy chọn): "thu" hoặc "chi".
     * `category` (Tùy chọn): Danh mục để lọc.
     * `time_range` (Bắt buộc): Khoảng thời gian: "today" (hôm nay), "yesterday" (hôm qua), "this_week" (tuần này), "this_month" (tháng này), hoặc "all" (tất cả). Mặc định là "today".
     * `limit` (Tùy chọn): Số lượng tối đa (mặc định là 10).

7. **`ghi_nhan_thu_chi`**: Khi người dùng ghi chép một giao dịch thu hoặc chi tiêu thông thường.
   - Arguments:
     * `transaction_type` (Bắt buộc): "thu" (nhận, kiếm được, lương...) hoặc "chi" (tiêu, trả tiền, mất tiền...).
     * `amount` (Bắt buộc): Số tiền thực tế (số dương).
     * `category` (Bắt buộc): Chọn 1 trong các danh mục chuẩn: {categories_list}. Quy tắc:
       - "Ăn uống": đồ ăn, thức uống, cafe, đi nhậu, phở...
       - "Di chuyển": grab, xăng xe, taxi, máy bay...
       - "Học tập": mua sách, học phí, khóa học...
       - "Mua sắm": mua quần áo, giày dép, Shopee, siêu thị...
       - "Lương": tiền lương, tiền thưởng, tiền công...
       - "Khác": tiền nhà, tiền nước, cho vay, trả nợ hoặc các khoản chung chung.
     * `description` (Bắt buộc): Mô tả ngắn gọn đã làm sạch từ đệm và viết hoa chữ cái đầu (ví dụ: "Ăn trưa", "Mua quần áo shopee").

---

### VÍ DỤ PHẢN HỒI (FEW-SHOT EXAMPLES):

- **Input**: "Thống kê cho tôi xem tháng này thế nào rồi robot"
  **Output**: {{"tool": "thong_ke_thu_chi", "arguments": {{}}}}

- **Input**: "Robot ơi hoàn tác khoản vừa nhập giùm nhé"
  **Output**: {{"tool": "huy_giao_dich_gan_nhat", "arguments": {{}}}}

- **Input**: "Xem ngân sách của tôi còn lại bao nhiêu vậy robot"
  **Output**: {{"tool": "xem_ngan_sach", "arguments": {{}}}}

- **Input**: "Đặt hạn mức chi tiêu ăn uống là ba triệu đồng nhé"
  **Output**: {{"tool": "thiet_lap_han_muc", "arguments": {{"category": "Ăn uống", "amount": 3000000}}}}

- **Input**: "Robot ơi sửa giao dịch vừa rồi thành tiền ăn trưa hết 50k nha"
  **Output**: {{"tool": "sua_giao_dich", "arguments": {{"transaction_id": -1, "amount": 50000, "category": "Ăn uống", "description": "Ăn trưa"}}}}

- **Input**: "Liệt kê các khoản chi tiêu hôm qua"
  **Output**: {{"tool": "truy_van_giao_dich", "arguments": {{"transaction_type": "chi", "time_range": "yesterday", "limit": 10}}}}

- **Input**: "an trua het nam muoi lam ngan"
  **Output**: {{"tool": "ghi_nhan_thu_chi", "arguments": {{"transaction_type": "chi", "amount": 55000, "category": "Ăn uống", "description": "Ăn trưa"}}}}

- **Input**: "Được chị gái cho hai triệu rưỡi nè robot"
  **Output**: {{"tool": "ghi_nhan_thu_chi", "arguments": {{"transaction_type": "thu", "amount": 2500000, "category": "Khác", "description": "Chị gái cho"}}}}

---

Hãy phân tích câu lệnh sau và trả về một chuỗi JSON duy nhất đại diện cho tool gọi, không có văn bản bao ngoài, không dùng block markdown ```json:
"{message}"
"""
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        result_text = response.text.strip()
        data = json.loads(result_text)
        
        tool_name = data.get("tool")
        args = data.get("arguments", {})
        
        # Bảo đảm category nếu có trong args phải hợp lệ
        if "category" in args and args["category"] not in categories_list:
            args["category"] = "Khác"
            
        return {
            "tool": tool_name,
            "arguments": args
        }
    except Exception as e:
        logging.error(f"Lỗi gọi Gemini API để định tuyến ý định: {e}")
        return None

def parse_with_gemini(message: str):
    """
    Hàm tương thích ngược. Trích xuất giao dịch từ Gemini.
    """
    parsed = parse_intent_with_gemini(message)
    if parsed and parsed["tool"] == "ghi_nhan_thu_chi":
        return parsed["arguments"]
    return None
