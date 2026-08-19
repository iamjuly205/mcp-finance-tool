# web/keyword_parser.py
import re
from typing import Optional, Dict, Any
import database

def remove_accents(input_str: str) -> str:
    s1 = 'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỊịỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
    s0 = 'AAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    res = []
    for c in input_str:
        idx = s1.find(c)
        if idx != -1:
            res.append(s0[idx])
        else:
            res.append(c)
    return "".join(res)

def extract_amount(text: str) -> float:
    # FIX K4: Loại bỏ các mẫu "ID số" trước để tránh đọc sai số ID thành số tiền
    # Ví dụ: "sửa ID 5 thành 200k" -> bỏ "id 5" trước khi tìm số tiền
    text = re.sub(r'\bid\s*\d+\b', '', text, flags=re.IGNORECASE)
    text_lower = text.lower().replace(",", ".")
    
    # 1. Hỗ trợ các trường hợp đặc biệt viết bằng chữ như "triệu rưỡi", "củ rưỡi", "trăm rưỡi", "chục rưỡi"
    rưỡi_patterns = [
        (r'\b(một\s+)?triệu\s+rưỡi\b', 1500000.0),
        (r'\b(một\s+)?trieu\s+ruoi\b', 1500000.0),
        (r'\b(một\s+)?củ\s+rưỡi\b', 1500000.0),
        (r'\b(một\s+)?cu\s+ruoi\b', 1500000.0),
        (r'\b(một\s+)?trăm\s+rưỡi\b', 150000.0),
        (r'\b(một\s+)?tram\s+ruoi\b', 150000.0),
        (r'\b(một\s+)?chục\s+rưỡi\b', 15000.0),
        (r'\b(một\s+)?chuc\s+ruoi\b', 15000.0),
    ]
    for pattern, val in rưỡi_patterns:
        if re.search(pattern, text_lower):
            return val

    # 2. Hỗ trợ đơn vị tắt dạng số + chữ: 1.5tr, 2 củ, 3 lít, 5 chục, 150k, 20 nghìn
    matches_with_unit = re.findall(
        r'(\d+(?:\.\d+)?)\s*(k|tr|triệu|trieu|đ|dong|đồng|cu|củ|lít|lit|chục|chuc|nghìn|nghin)', 
        text_lower
    )
    if matches_with_unit:
        val = float(matches_with_unit[0][0])
        unit = matches_with_unit[0][1]
        if unit in ['k', 'nghìn', 'nghin']:
            return val * 1000
        elif unit in ['chục', 'chuc']:
            return val * 10000
        elif unit in ['lít', 'lit']:
            return val * 100000
        elif unit in ['tr', 'triệu', 'trieu', 'cu', 'củ']:
            return val * 1000000
        else:
            return val
            
    # 3. Hỗ trợ khớp số thô (ví dụ: 50000, 100000, 300000)
    raw_matches = re.findall(r'\b(\d{4,9})\b', text_lower.replace(".", ""))
    if raw_matches:
        return float(raw_matches[0])
        
    return 0.0

def clean_voice_message(message: str) -> str:
    msg_clean = message
    
    # 1. Loại bỏ các cụm từ đệm phổ biến của giọng nói
    filler_patterns = [
        r'\brobot\s+ơi\b', r'\bxiaozhi\s+ơi\b', r'\bơi\b', r'\bnhé\b', r'\bnha\b', 
        r'\bgiùm\b', r'\bhộ\b', r'\bhãy\b', r'\bvới\b', r'\bà\b', r'\buhm\b',
        r'\bhôm\s+nay\b', r'\bhom\s+nay\b', r'\bvừa\b', r'\bvua\b', r'\bmới\b', r'\bmoi\b',
        r'\bcho\s+tôi\b', r'\bcho\s+to\b', r'\bhết\b', r'\bhet\b'
    ]
    for pattern in filler_patterns:
        msg_clean = re.sub(pattern, "", msg_clean, flags=re.IGNORECASE)
        
    # 2. Loại bỏ số tiền và đơn vị
    msg_clean = re.sub(r'\d+(?:\.\d+)?\s*(k|tr|triệu|trieu|đ|dong|đồng|cu|củ|lít|lit|chục|chuc)', "", msg_clean, flags=re.IGNORECASE)
    msg_clean = re.sub(r'\b\d{4,9}\b', "", msg_clean)
    msg_clean = re.sub(r'\b(triệu|trieu|củ|cu|trăm|tram|chục|chuc)\s+(rưỡi|ruoi)\b', "", msg_clean, flags=re.IGNORECASE)
    
    # Dọn dẹp khoảng trắng thừa
    msg_clean = re.sub(r'\s+', " ", msg_clean).strip()
    
    if msg_clean:
        msg_clean = msg_clean[0].upper() + msg_clean[1:]
    else:
        msg_clean = "Ghi nhận giao dịch"
        
    return msg_clean

def detect_category(msg: str, tx_type: Optional[str] = None) -> Optional[str]:
    """Phát hiện danh mục từ tin nhắn tiếng Việt có dấu (lowercase)."""
    mappings = database.get_keyword_mappings()
    if not mappings:
        return None
    # Ưu tiên: khớp tx_type trước, rồi từ khóa dài hơn (cụ thể hơn) lên trước
    if tx_type:
        mappings = sorted(mappings, key=lambda m: (m.get("type") == tx_type, len(m["keyword"])), reverse=True)
    else:
        mappings = sorted(mappings, key=lambda m: len(m["keyword"]), reverse=True)
    for m in mappings:
        kw = m["keyword"].lower().strip()
        if not kw:
            continue
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, msg):
            return m["category"]
    return None

def has_keyword(text: str, keywords: list) -> bool:
    return any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in keywords)

def route_intent_with_keywords(message: str) -> Optional[Dict[str, Any]]:
    """
    Phân loại câu lệnh người dùng thành 1 trong 7 MCP tools bằng từ khóa cục bộ.
    Nhận input tiếng Việt có dấu, so sánh trực tiếp không cần strip dấu.
    Trả về dict chứa tên tool và tham số, hoặc None nếu không nhận diện được.
    """
    msg_lower = message.lower()  # Tiếng Việt có dấu, chỉ lowercase

    # 1. TOOL: thong_ke_thu_chi
    if has_keyword(msg_lower, ["thống kê", "báo cáo tài chính", "báo cáo thu chi", "tổng thu chi", "thong ke", "bao cao"]):
        return {"tool": "thong_ke_thu_chi", "arguments": {}}

    # 2. TOOL: huy_giao_dich_gan_nhat (Undo)
    if has_keyword(msg_lower, ["hoàn tác", "hủy giao dịch", "xóa giao dịch", "xóa khoản vừa nhập", "xóa gần nhất",
                               "hoan tac", "huy giao dich", "xoa giao dich"]):
        return {"tool": "huy_giao_dich_gan_nhat", "arguments": {}}

    # 3. TOOL: xem_ngan_sach
    if has_keyword(msg_lower, ["xem ngân sách", "báo cáo ngân sách", "tình hình ngân sách", "còn bao nhiêu hạn mức",
                               "xem ngan sach"]):
        return {"tool": "xem_ngan_sach", "arguments": {}}

    # 4. TOOL: thiet_lap_han_muc (Set Budget)
    budget_keywords = [
        "cài hạn mức", "đặt hạn mức", "đặt ngân sách", "cài ngân sách",
        "thiết lập hạn mức", "thiết lập hạng mức", "thiết lập hạng mưc",
        "thiết lập ngân sách", "thiết lập định mức", "thiết lập",
        "giới hạn chi tiêu", "ngân sách cho", "định mức cho", "định mức",
        "hạn mức cho", "hạn mức", "hạng mức", "hạng mưc",
        "cai han muc", "dat han muc", "thiet lap han muc", "hang muc", "han muc", "dinh muc"
    ]
    if has_keyword(msg_lower, budget_keywords):
        amount = extract_amount(message)
        category = detect_category(msg_lower, "chi")
        if amount > 0 and category and category != "Khác":
            # Tìm thấy đủ thông tin: trả về tool thiet_lap_han_muc trực tiếp
            return {
                "tool": "thiet_lap_han_muc",
                "arguments": {"category": category, "amount": amount}
            }
        # Thiếu thông tin (category chưa có trong DB hoặc thiếu amount) -> Gemini LLM xử lý
        return None

    # 5. TOOL: sua_giao_dich (Edit)
    if has_keyword(msg_lower, ["sửa giao dịch", "cập nhật giao dịch", "sửa id", "thay đổi giao dịch",
                               "sua giao dich", "cap nhat giao dich"]):
        transaction_id = -1
        id_match = re.search(r'\bid\s*(\d+)\b', msg_lower)
        if id_match:
            transaction_id = int(id_match.group(1))

        amount = extract_amount(message)
        category = detect_category(msg_lower)

        # FIX N1: Dùng strict pattern giống ghi_nhan_thu_chi, tránh "thuê" bị nhận là "thu"
        tx_type = None
        thu_keywords_strict = ["lương", "nhận lương", "nhận tiền", "kiếm được", "thưởng", "thu nhập"]
        if has_keyword(msg_lower, thu_keywords_strict):
            tx_type = "thu"
        elif re.search(r'\bthu\b', msg_lower) and not re.search(r'\b(thu\s*chi|thuê)\b', msg_lower):
            tx_type = "thu"
        elif re.search(r'\b(chi|tiêu)\b', msg_lower):
            tx_type = "chi"

        if amount > 0 or category or tx_type:
            return {
                "tool": "sua_giao_dich",
                "arguments": {
                    "transaction_id": transaction_id,
                    "amount": amount if amount > 0 else None,
                    "category": category,
                    "transaction_type": tx_type,
                    "description": None
                }
            }
        return None

    # 6. TOOL: truy_van_giao_dich (Query)
    if has_keyword(msg_lower, ["liệt kê", "tìm kiếm", "truy vấn", "xem các khoản", "lịch sử giao dịch",
                               "liet ke", "tim kiem", "truy van", "lich su"]):
        time_range = "today"
        if any(kw in msg_lower for kw in ["hôm qua", "hom qua"]):
            time_range = "yesterday"
        elif any(kw in msg_lower for kw in ["tuần này", "tuan nay"]):
            time_range = "this_week"
        elif any(kw in msg_lower for kw in ["tháng này", "thang nay"]):
            time_range = "this_month"
        elif any(kw in msg_lower for kw in ["tất cả", "tat ca", "từ trước", "tu truoc"]):
            time_range = "all"
        elif any(kw in msg_lower for kw in ["hôm nay", "hom nay"]):
            time_range = "today"

        # FIX K7: "thu chi" = xem tất cả, không filter theo type
        tx_type = None
        if re.search(r'\bthu\s+chi\b', msg_lower):
            tx_type = None
        elif re.search(r'\bthu\b', msg_lower) and not re.search(r'\bthuê\b', msg_lower):
            tx_type = "thu"
        elif re.search(r'\b(chi|tiêu)\b', msg_lower):
            tx_type = "chi"

        category = detect_category(msg_lower, tx_type)

        return {
            "tool": "truy_van_giao_dich",
            "arguments": {
                "transaction_type": tx_type,
                "category": category,
                "time_range": time_range,
                "limit": 10
            }
        }

    # 7. TOOL: ghi_nhan_thu_chi (Giao dịch thu/chi thông thường)
    # Guard: Nếu câu chứa từ khóa ngân sách/cài đặt -> KHÔNG phải ghi nhận thủ công
    non_ghi_nhan_keywords = [
        "hạn mức", "hạng mức", "hạng mưc", "ngân sách", "định mức",
        "thiết lập", "cài đặt", "giới hạn", "sửa giao dịch", "cập nhật",
        "liệt kê", "danh sách", "truy vấn", "xem giao dịch", "thống kê",
        "han muc", "hang muc", "thiet lap", "ngan sach", "dinh muc"
    ]
    if has_keyword(msg_lower, non_ghi_nhan_keywords):
        return None  # Để Gemini LLM xử lý chính xác hơn

    amount = extract_amount(message)
    if amount > 0:
        # FIX K1: Phát hiện thu nhập chính xác hơn – tránh false positive: "thuê nhà" → vẫn là chi
        thu_keywords_strict = [
            "lương", "nhận lương", "nhận tiền", "kiếm được", "thưởng", "được cho",
            "được tặng", "thu nhập", "hoa hồng", "bán đồ", "thu nợ", "đòi nợ", "cổ tức"
        ]
        tx_type = "chi"
        if has_keyword(msg_lower, thu_keywords_strict):
            tx_type = "thu"
        elif re.search(r'\bthu\b', msg_lower) and not re.search(r'\b(thu\s*chi|thuê|thu\s+cùng)\b', msg_lower):
            tx_type = "thu"

        category = detect_category(msg_lower, tx_type)
        clean_desc = clean_voice_message(message)

        # Nếu không tìm thấy category -> Fallback sang LLM
        if category and category != "Khác":
            return {
                "tool": "ghi_nhan_thu_chi",
                "arguments": {
                    "transaction_type": tx_type,
                    "amount": amount,
                    "category": category,
                    "description": clean_desc
                }
            }

    return None

def parse_with_keywords(message: str) -> Optional[Dict[str, Any]]:
    """
    Hàm wrapper tương thích ngược với các test case ghi nhận giao dịch cũ.
    Trả về dict chứa các trường giao dịch nếu khớp ghi nhận giao dịch, ngược lại trả về None.
    """
    routed = route_intent_with_keywords(message)
    if routed and routed["tool"] == "ghi_nhan_thu_chi":
        args = routed["arguments"].copy()
        args["description"] = message.strip()
        return args
    return None
