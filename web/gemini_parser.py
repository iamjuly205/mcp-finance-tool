# web/gemini_parser.py
import os
import re
import json
import logging
from dotenv import load_dotenv
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai_available = False
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        genai_available = True
        logging.info("Gemini API da duoc cau hinh thanh cong.")
    except Exception as e:
        logging.error(f"Loi cau hinh Gemini API: {e}")
else:
    logging.warning("GEMINI_API_KEY khong duoc tim thay.")

import database

# --- SELF-LEARNING HELPERS ---

def _remove_accents_local(s: str) -> str:
    s1 = 'AAAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    s0 = 'AAAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    viet = 'AAAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    S1 = '\u00c0\u00c1\u00c2\u00c3\u00c8\u00c9\u00ca\u00cc\u00cd\u00d2\u00d3\u00d4\u00d5\u00d9\u00da\u00dd\u00e0\u00e1\u00e2\u00e3\u00e8\u00e9\u00ea\u00ec\u00ed\u00f2\u00f3\u00f4\u00f5\u00f9\u00fa\u00fd\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0\u1ea0\u1ea1\u1ea2\u1ea3\u1ea4\u1ea5\u1ea6\u1ea7\u1ea8\u1ea9\u1eaa\u1eab\u1eac\u1ead\u1eae\u1eaf\u1eb0\u1eb1\u1eb2\u1eb3\u1eb4\u1eb5\u1eb6\u1eb7\u1eb8\u1eb9\u1eba\u1ebb\u1ebc\u1ebd\u1ebe\u1ebf\u1ec0\u1ec1\u1ec2\u1ec3\u1ec4\u1ec5\u1ec6\u1ec7\u1ec8\u1ec9\u1eca\u1ecb\u1ecc\u1ecd\u1ece\u1ecf\u1ed0\u1ed1\u1ed2\u1ed3\u1ed4\u1ed5\u1ed6\u1ed7\u1ed8\u1ed9\u1eda\u1edb\u1edc\u1edd\u1ede\u1edf\u1ee0\u1ee1\u1ee2\u1ee3\u1ee4\u1ee5\u1ee6\u1ee7\u1ee8\u1ee9\u1eea\u1eeb\u1eec\u1eed\u1eee\u1eef\u1ef0\u1ef1\u1ef2\u1ef3\u1ef4\u1ef5\u1ef6\u1ef7\u1ef8\u1ef9'
    S0 = 'AAAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    res = []
    for c in s:
        idx = S1.find(c)
        res.append(S0[idx] if idx != -1 else c)
    return "".join(res)

_BLACKLIST_KW = {
    "ghi nhan giao dich", "thu chi", "tieu tien", "chi tieu",
    "giao dich", "hom nay", "hom qua", "vua roi", "gan nhat", "khac",
}

_WEAK = {
    "het", "da", "bi", "duoc", "co", "la", "va", "cho", "cua",
    "o", "tai", "bang", "voi", "di", "an", "mua", "chi", "thu",
    "tieu", "hom", "nay", "qua", "toi", "minh", "ban",
    "robot", "oi", "nhe", "nha", "gium",
}


def _extract_candidates(raw_message: str, primary_kw: str, category: str) -> List[str]:
    """
    Chỉ lưu keyword chính mà LLM đã trích xuất và tên category.
    Không sinh n-gram từ câu gốc vì dễ tạo keyword rác (ví dụ: 'đi chơi 2', 'mức đi chơi').
    LLM đã trích xuất đúng keyword rồi — tin tưởng kết quả đó.
    """
    seen = set()
    result = []

    def add(kw: str):
        kw = kw.strip().lower()
        if kw and len(kw) >= 2 and kw not in _BLACKLIST_KW and kw not in seen:
            seen.add(kw)
            result.append(kw)

    # 1. Primary keyword do LLM trích xuất (ưu tiên cao nhất, đã chính xác)
    if primary_kw:
        add(primary_kw)

    # 2. Tên category viết thường có dấu (để nhận diện khi user gõ tên category)
    cat_l = category.strip().lower()
    add(cat_l)

    # Lọc bỏ keyword đã có trong DB (trừ primary_kw)
    existing = {m["keyword"].lower().strip() for m in database.get_keyword_mappings()}
    pk_clean = primary_kw.strip().lower() if primary_kw else ""
    filtered = [c for c in result if c == pk_clean or c not in existing]
    return filtered



def _save_keywords(keywords: List[str], category: str, tx_type: str) -> List[str]:
    """Luu keyword vao DB, tra ve danh sach da luu thanh cong."""
    saved = []
    for kw in keywords:
        try:
            database.add_keyword_mapping(kw, category, tx_type)
            saved.append(kw)
        except Exception as ex:
            logging.warning(f"[SELF-LEARN] Khong luu duoc '{kw}': {ex}")
    if saved:
        logging.info(f"[SELF-LEARN] Hoc {len(saved)} keyword(s): {saved} -> '{category}' ({tx_type})")
    return saved


# --- MAIN PARSER ---

def parse_intent_with_gemini(message: str):
    """
    Dung Gemini API phan tich cau noi thanh lenh MCP.

    Vong lap tu hoc (Self-Learning Loop):
      Input la → LLM xu ly → Trich xuat bo keyword moi → Luu DB
      → Lan sau keyword_parser tu xu ly, khong can LLM nua.

    Tra ve dict voi truong 'learned_keywords' cho frontend hien thi.
    """
    if not genai_available:
        return None

    categories_list = database.get_all_categories()

    prompt = f"""Bạn là robot trợ lý tài chính Xiaozhi. Phân tích câu nói của người dùng thành lệnh MCP JSON.

### ĐẶC THÙ:
1. Loại bỏ các từ đệm: "robot ơi", "nhé", "giùm tôi", "uhm"...
2. Phục hồi dấu tiếng Việt bị mất nếu có.
3. Đổi số tiền bằng chữ sang số: "hai triệu rưỡi" -> 2500000, "một củ" -> 1000000, "ba lít" -> 300000.

### DANH MỤC HIỆN CÓ: {categories_list}
Nếu chưa có danh mục phù hợp -> TỰ TẠO danh mục mới (viết hoa chữ đầu, KHÔNG dùng "Khác").
Luôn trả về 'keyword' là cụm từ CỐT LÕI từ 1 đến 3 từ (viết chữ thường), ví dụ: "đi chơi", "thuê nhà", "tập gym".

### 7 CÔNG CỤ:
1. thong_ke_thu_chi: xem báo cáo tài chính tổng quan. Tham số: {{}}
2. huy_giao_dich_gan_nhat: hủy, xóa hoặc hoàn tác giao dịch vừa nhập. Tham số: {{}}
3. xem_ngan_sach: xem báo cáo hạn mức ngân sách tháng này. Tham số: {{}}
4. thiet_lap_han_muc: đặt hạn mức ngân sách cho một danh mục. Tham số: {{category, amount, keyword}}
5. sua_giao_dich: sửa thông tin một giao dịch đã lưu. Tham số: {{transaction_id (-1 nếu là giao dịch gần nhất), transaction_type?, amount?, category?, description?, keyword?}}
6. truy_van_giao_dich: liệt kê và lọc danh sách các giao dịch. Tham số: {{transaction_type?, category?, time_range ("today"/"yesterday"/"this_week"/"this_month"/"all"), limit?, keyword?}}
7. ghi_nhan_thu_chi: ghi nhận giao dịch thu hoặc chi. Tham số: {{transaction_type ("thu"/"chi"), amount, category, description, keyword}}

### VÍ DỤ:
- "Hom nay di choi het 1 trieu" -> {{"tool":"ghi_nhan_thu_chi","arguments":{{"transaction_type":"chi","amount":1000000,"category":"Đi chơi","description":"Đi chơi","keyword":"đi chơi"}}}}
- "Thue nha thang nay 5 trieu" -> {{"tool":"ghi_nhan_thu_chi","arguments":{{"transaction_type":"chi","amount":5000000,"category":"Nhà ở","description":"Thuê nhà","keyword":"thuê nhà"}}}}
- "Dat han muc di choi 2 trieu" -> {{"tool":"thiet_lap_han_muc","arguments":{{"category":"Đi chơi","amount":2000000,"keyword":"đi chơi"}}}}

Trả về JSON duy nhất, không dùng khối markdown:
"{message}"
"""
    try:
        import google.generativeai as genai
        import threading
        model = genai.GenerativeModel("gemini-2.5-flash")

        result_holder = [None]
        error_holder = [None]

        def call_gemini():
            try:
                result_holder[0] = model.generate_content(
                    prompt, generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                error_holder[0] = e

        t = threading.Thread(target=call_gemini, daemon=True)
        t.start()
        t.join(timeout=15)

        if error_holder[0]:
            raise error_holder[0]
        if result_holder[0] is None:
            logging.warning("[GEMINI TIMEOUT] Gemini API khong phan hoi trong 15 giay.")
            return None

        data = json.loads(result_holder[0].text.strip())
        tool_name = data.get("tool")
        args = data.get("arguments", {})

        # Sửa lỗi chính tả tiếng Việt phổ biến cho category và keyword
        for key in ["category", "keyword", "description"]:
            if key in args and isinstance(args[key], str):
                args[key] = args[key].replace("Di chơi", "Đi chơi").replace("di chơi", "đi chơi")
                args[key] = args[key].replace("Di ăn", "Đi ăn").replace("di ăn", "đi ăn")
                args[key] = args[key].replace("Di học", "Đi học").replace("di học", "đi học")
                args[key] = args[key].replace("Di làm", "Đi làm").replace("di làm", "đi làm")

        # --- SELF-LEARNING LOOP ---
        learned_keywords = []
        if "category" in args and args["category"]:
            cat_norm = database.normalize_category_name(args["category"])
            args["category"] = cat_norm

            primary_kw = args.get("keyword", "")
            tx_type = args.get("transaction_type", "chi")

            if not primary_kw and args.get("description"):
                desc_w = [w for w in args["description"].strip().lower().split()
                          if w not in _WEAK and len(w) >= 2]
                primary_kw = " ".join(desc_w[:3])

            candidates = _extract_candidates(message, primary_kw, cat_norm)
            if candidates:
                learned_keywords = _save_keywords(candidates, cat_norm, tx_type)

        return {
            "tool": tool_name,
            "arguments": args,
            "learned_keywords": learned_keywords
        }

    except Exception as e:
        logging.error(f"Loi goi Gemini API: {e}")
        return None


def parse_with_gemini(message: str):
    """Ham tuong thich nguoc."""
    parsed = parse_intent_with_gemini(message)
    if parsed and parsed["tool"] == "ghi_nhan_thu_chi":
        return parsed["arguments"]
    return None