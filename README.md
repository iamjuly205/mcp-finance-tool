# Xiaozhi Finance MCP (Model Context Protocol)

Dự án **Xiaozhi Finance MCP** cung cấp giải pháp quản lý tài chính cá nhân (thu chi, hạn mức ngân sách) tối ưu hóa cho Trợ lý giọng nói / Robot (Robot-only) thông qua giao thức **Model Context Protocol (MCP)**. Dự án cũng tích hợp sẵn một giao diện Web Visualizer cao cấp để demo và kiểm thử trực quan.

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
xiaozhi-finance-mcp-py/
├── database.py                 # Tầng truy xuất dữ liệu SQLite & logic nghiệp vụ ngân sách
├── server.py                   # MCP Server (FastMCP) khai báo 7 công cụ giao tiếp với AI
├── test_db.py                  # Script nhanh để kiểm tra khởi tạo và kết nối DB
├── requirements.txt            # Danh sách các thư viện Python phụ thuộc
├── .env.example                # File mẫu cấu hình biến môi trường (Gemini API Key)
├── .env                        # File cấu hình thực tế (chứa API Key)
├── quan_ly_thu_chi.db          # Cơ sở dữ liệu SQLite chính
├── server.log                  # Nhật ký hoạt động chi tiết của MCP Server (UTF-8)
├── tests/                      # Thư mục kiểm thử tự động
│   ├── test_database.py        # Test các hàm nghiệp vụ, múi giờ, fuzzy matching
│   └── test_server.py          # Test các MCP tools trong server.py
└── web/                        # Thư mục giao diện Web Visualizer & Chatbot Simulator
    ├── backend.py              # REST API server (FastAPI) & giả lập MCP Client
    ├── gemini_parser.py        # Module phân dịch câu nói tự nhiên sang JSON bằng Gemini API
    ├── run.py                  # Script khởi chạy nhanh giao diện Web
    ├── test_backend.py         # Test tự động cho các API của Web Visualizer
    └── static/                 # Tài nguyên giao diện tĩnh (HTML/CSS/JS Glassmorphic UI)
        ├── index.html
        ├── index.css
        └── main.js
```

---

## 🛠️ HƯỚNG DẪN CÀI ĐẶT & THIẾT LẬP MÔI TRƯỜNG

Dự án yêu cầu **Python 3.10** trở lên. Thực hiện các bước sau để thiết lập môi trường chạy dự án:

### 1. Tạo môi trường ảo (Virtual Environment)
Mở terminal tại thư mục gốc của dự án và chạy:
```bash
# Tạo môi trường ảo tên là .venv
python -m venv .venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Trên Windows (CMD):
.venv\Scripts\activate.bat
# Trên macOS / Linux:
source .venv/bin/activate
```

### 2. Cài đặt các thư viện phụ thuộc
Sau khi kích hoạt môi trường ảo, chạy lệnh cài đặt:
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Sao chép file `.env.example` thành `.env`:
```bash
copy .env.example .env
```
Mở file `.env` và điền khóa API của bạn từ [Google AI Studio](https://aistudio.google.com/) vào trường `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=AIzaSy...
```
*(Lưu ý: API Key này chỉ được sử dụng cho phần giả lập Chatbot trên giao diện Web Visualizer. Tầng MCP Server cốt lõi chạy hoàn toàn local qua SQLite và không yêu cầu API Key này).*

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN

### 1. Khởi chạy MCP Server (Giao diện stdio cho Robot/AI)
Tầng MCP Server hoạt động qua giao tiếp stdio (dòng vào/ra chuẩn) để tích hợp với các ứng dụng MCP Client như Claude Desktop.
Để khởi chạy thử server ở chế độ developer (hoặc dùng với công cụ kiểm thử mcp-cli):
```bash
fastmcp run server.py
```

### 2. Khởi chạy giao diện Web Visualizer & Chatbot Simulator
Để xem giao diện thống kê thu chi trực quan và giả lập hội thoại với Trợ lý AI:
```bash
python web/run.py
```
Sau đó, mở trình duyệt và truy cập: **`http://127.0.0.1:8000`**

Giao diện Web cung cấp:
*   Bảng phân tích tài chính thu chi, số dư trực quan.
*   Biểu đồ tròn cơ cấu chi tiêu thực tế.
*   Thanh tiến trình theo dõi ngân sách (tự động chuyển màu cảnh báo sang cam/đỏ khi đạt 80%/100%).
*   Khung Chat Simulator giúp gõ câu lệnh tiếng Việt tự nhiên và theo dõi quá trình dịch sang các lời gọi hàm MCP Tool thực tế (`JSON-RPC 2.0`).

---

## 🧪 HƯỚNG DẪN CHẠY KIỂM THỬ TỰ ĐỘNG

Dự án sử dụng thư viện `pytest` để chạy các unit test tự động. Tất cả dữ liệu kiểm thử được cô lập hoàn toàn trên DB ảo trong RAM, không ảnh hưởng đến dữ liệu thực tế.

Chạy toàn bộ test suite từ thư mục gốc:
```bash
pytest
```

Để xem thông tin in ra chi tiết của log khi chạy test:
```bash
pytest -v -s
```
