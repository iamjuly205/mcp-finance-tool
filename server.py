from mcp.server.fastmcp import FastMCP
from typing import Optional
from database import (
    init_db, 
    insert_giao_dich, 
    get_summary, 
    delete_last_transaction,
    query_giao_dich,
    update_giao_dich,
    set_ngan_sach,
    get_all_ngan_sach,
    find_matching_budget,
    get_monthly_spending_for_budget_category
)
import logging

# THIẾT LẬP HỆ THỐNG LOGGING CHUẨN PRODUCTION
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# KHỞI TẠO MCP SERVER
mcp = FastMCP("xiaozhi-finance-mcp")

def format_currency(amount: float) -> str:
    """Định dạng số tiền sang kiểu hiển thị Việt Nam, ví dụ: 50.000"""
    return f"{int(amount):,}".replace(",", ".")

# ----------------------------------------------------
# TOOL 1: GHI NHẬN THU CHI
# ----------------------------------------------------
@mcp.tool()
def ghi_nhan_thu_chi(transaction_type: str, amount: float, category: str, description: str = "") -> str:
    """
    Sử dụng công cụ này khi người dùng nói về việc tiêu tiền (chi) hoặc nhận tiền, kiếm được tiền (thu).
    
    Args:
        transaction_type: Bắt buộc là "thu" (nếu nhận tiền) hoặc "chi" (nếu tiêu tiền ra).
        amount: Số tiền giao dịch thực tế (phải lớn hơn 0).
        category: Phân loại hạng mục (Ví dụ: Ăn uống, Di chuyển, Tiền lương, Thưởng).
        description: Ghi chú chi tiết bối cảnh trích xuất từ câu nói.
    """
    if transaction_type not in ["thu", "chi"]:
        return "Lỗi: Loại giao dịch chỉ có thể là 'thu' hoặc 'chi'."
    if amount <= 0:
        return "Lỗi: Số tiền phải lớn hơn 0."
        
    logging.info(f"Robot kích hoạt Tool: ghi_nhan_thu_chi | type={transaction_type}, amount={amount}, category={category}")
    
    try:
        # Ghi nhận giao dịch trước
        insert_giao_dich(transaction_type, amount, category, description)
        
        hanh_dong = "chi tiêu" if transaction_type == "chi" else "thu nhập"
        so_tien_doc = format_currency(amount)
        text_response = f"Đã ghi nhận khoản {hanh_dong} {so_tien_doc} đồng cho hạng mục {category}."
        
        # Kiểm tra cảnh báo hạn mức ngân sách (nếu là khoản chi)
        if transaction_type == "chi":
            match = find_matching_budget(category)
            if match:
                budget_cat, budget_amount = match
                # Tính tổng đã tiêu trong tháng này cho danh mục ngân sách đó
                spent_amount = get_monthly_spending_for_budget_category(budget_cat)
                
                spent_str = format_currency(spent_amount)
                limit_str = format_currency(budget_amount)
                
                if spent_amount > budget_amount:
                    text_response += f" Cảnh báo: Bạn đã chi tiêu vượt hạn mức của danh mục {budget_cat} ({spent_str}/{limit_str} đồng)!"
                elif spent_amount >= budget_amount * 0.8:
                    percent = int((spent_amount / budget_amount) * 100)
                    text_response += f" Cảnh báo: Chi tiêu cho {budget_cat} đã đạt {percent}% hạn mức tháng ({spent_str}/{limit_str} đồng)!"
        
        logging.info(f"Phản hồi TTS: {text_response}")
        return text_response
        
    except Exception as e:
        logging.error(f"Lỗi xử lý Database: {e}")
        return "Hệ thống đang gặp lỗi, chưa thể lưu giao dịch này."

# ----------------------------------------------------
# TOOL 2: BÁO CÁO THỐNG KÊ
# ----------------------------------------------------
@mcp.tool()
def thong_ke_thu_chi() -> str:
    """
    Sử dụng công cụ này khi người dùng muốn biết tổng quan tài chính, hỏi xem đã tiêu bao nhiêu tiền, hoặc kiếm được tổng cộng bao nhiêu.
    """
    logging.info("Robot kích hoạt Tool: thong_ke_thu_chi")
    try:
        data = get_summary()
        thu_str = format_currency(data['tong_thu'])
        chi_str = format_currency(data['tong_chi'])
        
        text_response = f"Báo cáo tài chính hiện tại: Tổng thu là {thu_str} đồng, tổng chi là {chi_str} đồng."
        logging.info(f"Phản hồi TTS: {text_response}")
        return text_response
    except Exception as e:
        logging.error(f"Lỗi thống kê: {e}")
        return "Lỗi hệ thống, không thể tính toán dữ liệu thống kê lúc này."

# ----------------------------------------------------
# TOOL 3: HỦY GIAO DỊCH (UNDO)
# ----------------------------------------------------
@mcp.tool()
def huy_giao_dich_gan_nhat() -> str:
    """
    Sử dụng công cụ này khi người dùng yêu cầu xóa, hủy, hoặc hoàn tác khoản tiền vừa ghi nhận sai hoặc nói nhầm.
    """
    logging.info("Robot kích hoạt Tool: huy_giao_dich_gan_nhat")
    try:
        success = delete_last_transaction()
        if success:
            text_response = "Đã hủy giao dịch gần nhất thành công."
        else:
            text_response = "Không tìm thấy giao dịch nào để hủy."
            
        logging.info(f"Phản hồi TTS: {text_response}")
        return text_response
    except Exception as e:
        logging.error(f"Lỗi xóa giao dịch: {e}")
        return "Đã xảy ra lỗi, không thể hủy giao dịch."

# ----------------------------------------------------
# TOOL 4: TRUY VẤN GIAO DỊCH (QUERY)
# ----------------------------------------------------
@mcp.tool()
def truy_van_giao_dich(
    transaction_type: Optional[str] = None, 
    category: Optional[str] = None, 
    time_range: str = "today", 
    limit: int = 10
) -> str:
    """
    Truy vấn và liệt kê danh sách các giao dịch thu chi từ cơ sở dữ liệu dựa trên bộ lọc thời gian, loại giao dịch hoặc hạng mục.
    
    Args:
        transaction_type: Lọc theo loại giao dịch: "thu" hoặc "chi". Nếu để trống sẽ lấy cả hai.
        category: Lọc theo hạng mục cụ thể (Ví dụ: Ăn uống, Di chuyển).
        time_range: Khoảng thời gian: "today" (hôm nay), "yesterday" (hôm qua), "this_week" (tuần này), "this_month" (tháng này), "all" (tất cả). Mặc định là "today".
        limit: Số lượng giao dịch tối đa hiển thị (Mặc định là 10).
    """
    logging.info(f"Robot kích hoạt Tool: truy_van_giao_dich | type={transaction_type}, category={category}, time_range={time_range}")
    try:
        txs = query_giao_dich(transaction_type, category, time_range, limit)
        if not txs:
            time_labels = {
                "today": "hôm nay",
                "yesterday": "hôm qua",
                "this_week": "tuần này",
                "this_month": "tháng này",
                "all": "từ trước tới nay"
            }
            label = time_labels.get(time_range, time_range)
            return f"Không tìm thấy giao dịch nào phù hợp trong {label}."
            
        lines = []
        for tx in txs:
            amount_str = format_currency(tx["amount"])
            type_label = "Thu" if tx["type"] == "thu" else "Chi"
            desc = f" ({tx['description']})" if tx["description"] else ""
            lines.append(f"- ID #{tx['id']}: {type_label} {amount_str}đ - {tx['category']}{desc} lúc {tx['created_at']}")
            
        text_response = "Danh sách giao dịch tìm thấy:\n" + "\n".join(lines)
        return text_response
    except Exception as e:
        logging.error(f"Lỗi truy vấn: {e}")
        return "Đã xảy ra lỗi khi truy vấn danh sách giao dịch."

# ----------------------------------------------------
# TOOL 5: SỬA GIAO DỊCH (EDIT)
# ----------------------------------------------------
@mcp.tool()
def sua_giao_dich(
    transaction_id: int = -1,
    transaction_type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Sửa đổi thông tin của một giao dịch đã lưu trong cơ sở dữ liệu.
    
    Args:
        transaction_id: ID của giao dịch cần sửa. Nếu không biết ID hoặc muốn sửa giao dịch gần nhất vừa thêm, hãy truyền -1.
        transaction_type: Loại giao dịch mới: "thu" hoặc "chi".
        amount: Số tiền mới (phải lớn hơn 0).
        category: Hạng mục mới.
        description: Ghi chú mới.
    """
    logging.info(f"Robot kích hoạt Tool: sua_giao_dich | id={transaction_id}")
    try:
        if transaction_type is not None and transaction_type not in ["thu", "chi"]:
            return "Lỗi: Loại giao dịch chỉ có thể là 'thu' hoặc 'chi'."
        if amount is not None and amount <= 0:
            return "Lỗi: Số tiền phải lớn hơn 0."
            
        success = update_giao_dich(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=amount,
            category=category,
            description=description
        )
        
        if success:
            target_str = "gần nhất" if transaction_id == -1 else f"ID #{transaction_id}"
            return f"Đã cập nhật thành công giao dịch {target_str}."
        else:
            return "Không tìm thấy giao dịch tương ứng để cập nhật."
    except Exception as e:
        logging.error(f"Lỗi khi sửa giao dịch: {e}")
        return "Đã xảy ra lỗi trong quá trình cập nhật giao dịch."

# ----------------------------------------------------
# TOOL 6: THIẾT LẬP HẠN MỨC CHI TIÊU (BUDGET)
# ----------------------------------------------------
@mcp.tool()
def thiet_lap_han_muc(category: str, amount: float) -> str:
    """
    Thiết lập hoặc cập nhật hạn mức chi tiêu hàng tháng cho một danh mục (ví dụ: Ăn uống, Mua sắm).
    
    Args:
        category: Danh mục chi tiêu muốn thiết lập hạn mức (Ví dụ: Ăn uống).
        amount: Số tiền hạn mức tối đa cho cả tháng (phải lớn hơn 0).
    """
    if amount <= 0:
        return "Lỗi: Số tiền hạn mức phải lớn hơn 0."
        
    logging.info(f"Robot kích hoạt Tool: thiet_lap_han_muc | category={category}, amount={amount}")
    try:
        set_ngan_sach(category, amount)
        amount_str = format_currency(amount)
        return f"Đã thiết lập hạn mức chi tiêu hàng tháng cho danh mục {category} là {amount_str} đồng."
    except Exception as e:
        logging.error(f"Lỗi thiết lập ngân sách: {e}")
        return "Đã xảy ra lỗi, không thể thiết lập hạn mức."

# ----------------------------------------------------
# TOOL 7: XEM TÌNH HÌNH NGÂN SÁCH (BUDGET REPORT)
# ----------------------------------------------------
@mcp.tool()
def xem_ngan_sach() -> str:
    """
    Xem danh sách hạn mức chi tiêu hàng tháng và tình hình chi tiêu thực tế của từng danh mục trong tháng này.
    """
    logging.info("Robot kích hoạt Tool: xem_ngan_sach")
    try:
        budgets = get_all_ngan_sach()
        if not budgets:
            return "Hiện tại bạn chưa thiết lập hạn mức chi tiêu nào."
            
        lines = []
        for b in budgets:
            cat = b["category"]
            limit = b["amount"]
            spent = get_monthly_spending_for_budget_category(cat)
            
            limit_str = format_currency(limit)
            spent_str = format_currency(spent)
            
            percent = int((spent / limit) * 100) if limit > 0 else 0
            remaining = limit - spent
            
            if remaining < 0:
                over = abs(remaining)
                status = f" -> ĐÃ VƯỢT HẠN MỨC {format_currency(over)}đ"
            else:
                status = f" -> Còn lại {format_currency(remaining)}đ"
                
            lines.append(f"- {cat}: Đã tiêu {spent_str}đ / Hạn mức {limit_str}đ ({percent}%){status}")
            
        text_response = "Báo cáo hạn mức chi tiêu tháng này:\n" + "\n".join(lines)
        return text_response
    except Exception as e:
        logging.error(f"Lỗi xem ngân sách: {e}")
        return "Đã xảy ra lỗi khi truy vấn thông tin ngân sách."

# ĐIỂM CHẠY ỨNG DỤNG
if __name__ == "__main__":
    logging.info("Khởi chạy Database...")
    init_db()
    
    logging.info("MCP Server Quản lý Thu Chi đang hoạt động ổn định qua giao thức Stdio...")
    mcp.run(transport='stdio')