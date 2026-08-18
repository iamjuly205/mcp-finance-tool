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
    Tu cau goc + keyword LLM, trich xuat bo tu khoa de luu vao DB.
    Muc tieu: lan sau input tuong tu, keyword_parser tu xu ly khong can LLM.
    """
    seen = set()
    result = []

    def add(kw: str):
        kw = kw.strip().lower()
        if kw and len(kw) >= 3 and kw not in _BLACKLIST_KW and kw not in seen:
            seen.add(kw)
            result.append(kw)

    # 1. Primary keyword tu LLM (uu tien cao nhat)
    if primary_kw:
        add(primary_kw)

    # 2. Ten category viet thuong (co dau + khong dau)
    cat_l = category.strip().lower()
    add(cat_l)
    cat_na = _remove_accents_local(cat_l)
    if cat_na != cat_l:
        add(cat_na)

    # 3. N-gram tu cau goc, chi lay gram lien quan den keyword/category
    msg = re.sub(
        r'\d+(?:[.,]\d+)?\s*(k|tr|trieu|dong|cu|lit|chuc|d)\b', '', raw_message, flags=re.IGNORECASE
    )
    msg = re.sub(r'\b\d{3,}\b', '', msg)
    msg = re.sub(r'\s+', ' ', msg).strip().lower()
    msg_na = _remove_accents_local(msg)

    pk_na = _remove_accents_local(primary_kw.lower()) if primary_kw else ""
    words_na = msg_na.split()

    for i in range(len(words_na)):
        for n in range(1, 4):
            if i + n > len(words_na):
                break
            gram_na = " ".join(words_na[i:i+n])
            gram_words = gram_na.split()
            # Bo qua gram toan tu yeu
            if all(w in _WEAK for w in gram_words):
                continue
            relevant = (
                (pk_na and (pk_na in gram_na or gram_na in pk_na)) or
                (cat_na and (cat_na in gram_na or gram_na in cat_na))
            )
            if relevant:
                # Tim lai gram co dau tu words goc
                words_orig = msg.split()
                gram_orig = " ".join(words_orig[i:i+n]) if i+n <= len(words_orig) else gram_na
                add(gram_orig)
                if gram_na != gram_orig:
                    add(gram_na)

    # Loai tu khoa da co trong DB (tru primary keyword)
    existing = {m["keyword"].lower().strip() for m in database.get_keyword_mappings()}
    pk_clean = primary_kw.strip().lower() if primary_kw else ""
    filtered = [c for c in result if c == pk_clean or c not in existing]
    return filtered[:6]


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

    prompt = f"""Ban la robot tro ly tai chinh Xiaozhi. Phan tich cau noi nguoi dung thanh lenh MCP JSON.

### DAC THU:
1. Bo tu dem: "robot oi", "nhe", "gium toi", "um"...
2. Phuc hoi dau tieng Viet bi mat.
3. Doi so tien bang chu: "hai trieu ruoi"->2500000, "mot cu"->1000000, "ba lit"->300000.

### DANH MUC HIEN CO: {categories_list}
Neu chua co -> TU TAO danh muc moi (viet hoa chu dau, KHONG dung "Khac").
Luon tra ve 'keyword' la cum tu COT LOI 1-3 tu (chu thuong), vi du: "di choi", "thue nha", "tap gym".

### 7 CONG CU:
1. thong_ke_thu_chi: xem bao cao. Args: {{}}
2. huy_giao_dich_gan_nhat: huy/xoa/hoan tac. Args: {{}}
3. xem_ngan_sach: xem han muc. Args: {{}}
4. thiet_lap_han_muc: dat han muc. Args: {{category, amount, keyword}}
5. sua_giao_dich: sua giao dich. Args: {{transaction_id(-1=gan nhat), transaction_type?, amount?, category?, description?, keyword?}}
6. truy_van_giao_dich: liet ke. Args: {{transaction_type?, category?, time_range("today"/"yesterday"/"this_week"/"this_month"/"all"), limit?, keyword?}}
7. ghi_nhan_thu_chi: ghi thu/chi. Args: {{transaction_type("thu"/"chi"), amount, category, description, keyword}}

### VI DU:
- "Hom nay di choi het 1 trieu" -> {{"tool":"ghi_nhan_thu_chi","arguments":{{"transaction_type":"chi","amount":1000000,"category":"Di choi","description":"Di choi","keyword":"di choi"}}}}
- "Thue nha thang nay 5 trieu" -> {{"tool":"ghi_nhan_thu_chi","arguments":{{"transaction_type":"chi","amount":5000000,"category":"Nha o","description":"Thue nha","keyword":"thue nha"}}}}
- "Dat han muc di choi 2 trieu" -> {{"tool":"thiet_lap_han_muc","arguments":{{"category":"Di choi","amount":2000000,"keyword":"di choi"}}}}

Tra ve JSON duy nhat, khong markdown:
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