# DANH SÁCH CÂU LỆNH MẪU CHO ROBOT / AI AGENT (ROBOT-ONLY SPEECH COMMANDS)

Tài liệu này cung cấp bộ câu lệnh mẫu tiếng Việt dùng để huấn luyện hoặc làm tài liệu ngữ cảnh (few-shot) cho Robot/AI Agent. Đảm bảo ánh xạ chính xác câu nói tự nhiên (kể cả không dấu hoặc thiếu thông tin) sang 7 MCP Tools tương ứng của **Xiaozhi Finance MCP**.

---

## 1. Tool: `ghi_nhan_thu_chi`
*Sử dụng khi người dùng muốn ghi chép một khoản tiền chi ra hoặc thu vào.*

*   **Câu lệnh đầy đủ thông tin (Có dấu):**
    1. *"Hôm nay ăn trưa phở bò hết 55 nghìn đồng"*
    2. *"Vừa đi grab đi làm hết 35k"*
    3. *"Nhận được tiền lương tháng này 15 triệu"*
*   **Câu lệnh không dấu / viết tắt:**
    4. *"an com 40k"*
    5. *"di grab het 30k"*
    6. *"nhan luong 12tr"*
*   **Câu lệnh thiếu thông tin (Chung chung):**
    7. *"Vừa tiêu mất 100k"* (Hệ thống tự động xếp vào mục "Khác", mô tả "Chi tiêu chung")
    8. *"Có thêm 500 nghìn"* (Hệ thống tự động xếp vào mục "Khác", mô tả "Thu nhập chung")

---

## 2. Tool: `thong_ke_thu_chi`
*Sử dụng khi người dùng hỏi về tổng quan tình hình tài chính tổng thu, tổng chi.*

*   **Câu lệnh tự nhiên:**
    1. *"Tổng hợp thu chi của tôi từ trước tới giờ thế nào rồi?"*
    2. *"Thống kê tài chính hiện tại của tôi ra sao robot?"*
    3. *"Xem giúp tôi đã tiêu bao nhiêu và kiếm được bao nhiêu tiền rồi"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"thong ke thu chi"*
    5. *"bao cao tai chinh"*
    6. *"xem tong thu chi"*

---

## 3. Tool: `huy_giao_dich_gan_nhat` (Undo)
*Sử dụng khi người dùng muốn hoàn tác hoặc xóa bỏ giao dịch vừa mới ghi nhận sai.*

*   **Câu lệnh tự nhiên:**
    1. *"Hủy khoản tiền vừa nhập đi robot ơi, tôi nói nhầm"*
    2. *"Hoàn tác giao dịch gần nhất giúp tôi với"*
    3. *"Xóa khoản chi vừa rồi đi nhé"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"huy giao dich"*
    5. *"hoan tac"*
    6. *"xoa khoan vua nhap"*

---

## 4. Tool: `truy_van_giao_dich` (Query)
*Sử dụng khi người dùng muốn xem danh sách các giao dịch cụ thể theo bộ lọc thời gian hoặc danh mục.*

*   **Câu lệnh tự nhiên:**
    1. *"Hôm nay tôi đã tiêu những khoản gì rồi?"*
    2. *"Liệt kê các khoản chi tiêu liên quan đến Ăn uống trong tuần này"*
    3. *"Tìm giúp tôi xem hôm qua có giao dịch thu nhập nào không"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"xem cac khoan chi hom nay"*
    5. *"truy van giao dich an uong"*
    6. *"liet ke chi tieu tuan nay"*

---

## 5. Tool: `sua_giao_dich` (Edit)
*Sử dụng khi người dùng muốn cập nhật lại thông tin (số tiền, danh mục, mô tả) của một giao dịch.*

*   **Câu lệnh tự nhiên:**
    1. *"Sửa khoản tiền ăn sáng vừa rồi thành 30 nghìn nhé"*
    2. *"Cập nhật lại giao dịch ID số 3 thành chi tiêu 50k mục di chuyển"*
    3. *"Thay đổi mô tả của khoản chi gần nhất thành ăn bún riêu"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"sua giao dich gan nhat thanh 50k"*
    5. *"sua id 5 thanh luong 10tr"*
    6. *"sua tien do xang thanh 40k"*

---

## 6. Tool: `thiet_lap_han_muc` (Set Budget)
*Sử dụng khi người dùng muốn cài đặt hạn mức chi tiêu tối đa trong tháng cho một hạng mục cụ thể.*

*   **Câu lệnh tự nhiên:**
    1. *"Đặt hạn mức chi tiêu cho danh mục Ăn uống tháng này là 3 triệu đồng"*
    2. *"Giới hạn tiền Mua sắm tháng này là 5 triệu nhé robot"*
    3. *"Cài đặt ngân sách di chuyển mỗi tháng tối đa 1 triệu"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"dat ngan sach an uong 2tr"*
    5. *"han muc mua sam 3 trieu"*
    6. *"cai han muc di chuyen 1tr"*

---

## 7. Tool: `xem_ngan_sach` (Budget Report)
*Sử dụng khi người dùng muốn kiểm tra tình hình sử dụng hạn mức ngân sách tháng.*

*   **Câu lệnh tự nhiên:**
    1. *"Tình hình ngân sách các danh mục tháng này thế nào rồi robot?"*
    2. *"Tôi đã tiêu bao nhiêu phần trăm hạn mức Ăn uống rồi?"*
    3. *"Xem báo cáo chi tiết ngân sách chi tiêu tháng này"*
*   **Câu lệnh rút gọn / Không dấu:**
    4. *"xem ngan sach"*
    5. *"con bao nhieu han muc"*
    6. *"bao cao ngan sach"*
