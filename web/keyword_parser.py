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

    # 2. Hỗ trợ đơn vị tắt dạng số + chữ: 1.5tr, 2 củ, 3 lít, 5 chục, 150k
    matches_with_unit = re.findall(
        r'(\d+(?:\.\d+)?)\s*(k|tr|triệu|trieu|đ|dong|đồng|cu|củ|lít|lit|chục|chuc)', 
        text_lower
    )
    if matches_with_unit:
        val = float(matches_with_unit[0][0])
        unit = matches_with_unit[0][1]
        if unit in ['k']:
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

def detect_category(msg_no_accent: str) -> Optional[str]:
    mappings = database.get_keyword_mappings()
    for m in mappings:
        kw = m["keyword"].lower()
        kw_no_accent = remove_accents(kw)
        pattern = r'\b' + re.escape(kw_no_accent) + r'\b'
        if re.search(pattern, msg_no_accent):
            return m["category"]
    return None

def has_keyword(text: str, keywords: list) -> bool:
    return any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in keywords)

def route_intent_with_keywords(message: str) -> Optional[Dict[str, Any]]:
    """
    Phân loại câu lệnh người dùng thành 1 trong 7 MCP tools bằng từ khóa cục bộ.
    Trả về dict chứa tên tool và tham số, hoặc None nếu không nhận diện được.
    """
    msg_lower = message.lower()
    msg_no_accent = remove_accents(msg_lower)
    
    # 1. TOOL: thong_ke_thu_chi
    if has_keyword(msg_no_accent, ["thong ke", "bao cao tai chinh", "bao cao thu chi", "tong thu chi"]):
        return {"tool": "thong_ke_thu_chi", "arguments": {}}
        
    # 2. TOOL: huy_giao_dich_gan_nhat (Undo)
    if has_keyword(msg_no_accent, ["hoan tac", "huy giao dich", "xoa giao dich", "xoa khoan vua nhap", "xoa gan nhat"]):
        return {"tool": "huy_giao_dich_gan_nhat", "arguments": {}}
        
    # 3. TOOL: xem_ngan_sach
    if has_keyword(msg_no_accent, ["xem ngan sach", "bao cao ngan sach", "tinh hinh ngan sach", "con bao nhieu han muc"]):
        return {"tool": "xem_ngan_sach", "arguments": {}}
        
    # 4. TOOL: thiet_lap_han_muc (Set Budget)
    if has_keyword(msg_no_accent, ["cai han muc", "dat han muc", "dat ngan sach", "cai ngan sach", "thiet lap han muc", "gioi han chi tieu"]):
        amount = extract_amount(message)
        category = detect_category(msg_no_accent)
        if amount > 0 and category:
            return {
                "tool": "thiet_lap_han_muc",
                "arguments": {"category": category, "amount": amount}
            }
        return None
        
    # 5. TOOL: sua_giao_dich (Edit)
    if has_keyword(msg_no_accent, ["sua giao dich", "cap nhat giao dich", "sua id", "thay doi giao dich"]):
        transaction_id = -1
        id_match = re.search(r'\bid\s*(\d+)\b', msg_no_accent)
        if id_match:
            transaction_id = int(id_match.group(1))
            
        amount = extract_amount(message)
        category = detect_category(msg_no_accent)
        
        tx_type = None
        if "thu" in msg_no_accent or "luong" in msg_no_accent:
            tx_type = "thu"
        elif "chi" in msg_no_accent or "tieu" in msg_no_accent:
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
    if has_keyword(msg_no_accent, ["liet ke", "tim kiem", "truy van", "xem cac khoan", "lich su giao dich"]):
        time_range = "today"
        if "hom qua" in msg_no_accent:
            time_range = "yesterday"
        elif "tuan nay" in msg_no_accent:
            time_range = "this_week"
        elif "thang nay" in msg_no_accent:
            time_range = "this_month"
        elif "tat ca" in msg_no_accent or "tu truoc" in msg_no_accent:
            time_range = "all"
            
        tx_type = None
        if "thu" in msg_no_accent or "luong" in msg_no_accent:
            tx_type = "thu"
        elif "chi" in msg_no_accent or "tieu" in msg_no_accent:
            tx_type = "chi"
            
        category = detect_category(msg_no_accent)
        
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
    amount = extract_amount(message)
    if amount > 0:
        category = detect_category(msg_no_accent)
        tx_type = "chi"
        if has_keyword(msg_no_accent, ["thu", "luong", "nhan", "kiem", "thuong", "cong", "duoc cho"]):
            tx_type = "thu"
            
        clean_desc = clean_voice_message(message)
        
        # Nếu không tìm thấy category, hoặc khớp category "Khác" -> Fallback sang LLM để phân loại tốt hơn
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
