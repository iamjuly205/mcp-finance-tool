import sqlite3
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

DB_FILE = "quan_ly_thu_chi.db"
VIETNAM_TZ = timezone(timedelta(hours=7))

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thu_chi_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tạo index cho created_at để truy vấn nhanh hơn
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_thu_chi_logs_created_at ON thu_chi_logs(created_at)")
        
        # Tạo bảng ngân sách chi tiêu hàng tháng
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ngan_sach (
                category TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tự động gộp & dọn dẹp các bản ghi ngân sách trùng lặp hoa/thường
        cursor.execute("SELECT category, amount FROM ngan_sach")
        rows = cursor.fetchall()
        if rows:
            merged = {}
            for c, a in rows:
                norm_c = normalize_category_name(c)
                merged[norm_c] = a
            cursor.execute("DELETE FROM ngan_sach")
            for norm_c, a in merged.items():
                cursor.execute("INSERT INTO ngan_sach (category, amount) VALUES (?, ?)", (norm_c, a))
            conn.commit()

        
        # Tạo bảng keyword phân loại giao dịch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_mapping_keyword ON keywords_mapping(keyword)")
        
        # Seed default keywords if empty
        cursor.execute("SELECT COUNT(*) FROM keywords_mapping")
        if cursor.fetchone()[0] == 0:
            default_keywords = [
                # --- ĂN UỐNG (chi) ---
                ("ăn", "Ăn uống", "chi"), ("uống", "Ăn uống", "chi"), ("ăn uống", "Ăn uống", "chi"),
                ("ăn trưa", "Ăn uống", "chi"), ("ăn sáng", "Ăn uống", "chi"), ("ăn tối", "Ăn uống", "chi"),
                ("ăn vặt", "Ăn uống", "chi"), ("đi ăn", "Ăn uống", "chi"), ("cơm", "Ăn uống", "chi"),
                ("bún", "Ăn uống", "chi"), ("phở", "Ăn uống", "chi"), ("mì", "Ăn uống", "chi"),
                ("hủ tiếu", "Ăn uống", "chi"), ("cháo", "Ăn uống", "chi"), ("bánh", "Ăn uống", "chi"),
                ("lẩu", "Ăn uống", "chi"), ("nướng", "Ăn uống", "chi"), ("nhậu", "Ăn uống", "chi"),
                ("đi nhậu", "Ăn uống", "chi"), ("bia", "Ăn uống", "chi"), ("rượu", "Ăn uống", "chi"),
                ("nước ngọt", "Ăn uống", "chi"), ("nước lọc", "Ăn uống", "chi"), ("cafe", "Ăn uống", "chi"),
                ("cà phê", "Ăn uống", "chi"), ("trà sữa", "Ăn uống", "chi"), ("sinh tố", "Ăn uống", "chi"),
                ("nước ép", "Ăn uống", "chi"), ("kem", "Ăn uống", "chi"), ("hoa quả", "Ăn uống", "chi"),
                ("trái cây", "Ăn uống", "chi"), ("quán", "Ăn uống", "chi"), ("nhà hàng", "Ăn uống", "chi"),
                ("cơm tấm", "Ăn uống", "chi"), ("bún bò", "Ăn uống", "chi"), ("bún riêu", "Ăn uống", "chi"),
                ("bánh mì", "Ăn uống", "chi"), ("pizza", "Ăn uống", "chi"), ("kfc", "Ăn uống", "chi"),
                ("lotteria", "Ăn uống", "chi"), ("jollibee", "Ăn uống", "chi"), ("mcdonald", "Ăn uống", "chi"),
                ("bánh tráng", "Ăn uống", "chi"), ("ốc", "Ăn uống", "chi"), ("xôi", "Ăn uống", "chi"),
                ("chè", "Ăn uống", "chi"), ("sữa", "Ăn uống", "chi"), ("ăn tiệc", "Ăn uống", "chi"),
                ("liên hoan", "Ăn uống", "chi"),
                
                # --- DI CHUYỂN (chi) ---
                ("xe", "Di chuyển", "chi"), ("xăng", "Di chuyển", "chi"), ("đổ xăng", "Di chuyển", "chi"),
                ("grab", "Di chuyển", "chi"), ("be", "Di chuyển", "chi"), ("gojek", "Di chuyển", "chi"),
                ("xanh sm", "Di chuyển", "chi"), ("taxi", "Di chuyển", "chi"), ("bus", "Di chuyển", "chi"),
                ("xe bus", "Di chuyển", "chi"), ("xe buýt", "Di chuyển", "chi"), ("tàu", "Di chuyển", "chi"),
                ("vé tàu", "Di chuyển", "chi"), ("máy bay", "Di chuyển", "chi"), ("vé máy bay", "Di chuyển", "chi"),
                ("đi lại", "Di chuyển", "chi"), ("di chuyển", "Di chuyển", "chi"), ("gửi xe", "Di chuyển", "chi"),
                ("vé xe", "Di chuyển", "chi"), ("xe khách", "Di chuyển", "chi"), ("xe đò", "Di chuyển", "chi"),
                ("limousine", "Di chuyển", "chi"), ("thuê xe", "Di chuyển", "chi"), ("sửa xe", "Di chuyển", "chi"),
                ("bảo dưỡng xe", "Di chuyển", "chi"), ("rửa xe", "Di chuyển", "chi"), ("thay nhớt", "Di chuyển", "chi"),
                ("metro", "Di chuyển", "chi"),
                
                # --- MUA SẮM (chi) ---
                ("mua", "Mua sắm", "chi"), ("sắm", "Mua sắm", "chi"), ("mua sắm", "Mua sắm", "chi"),
                ("shopee", "Mua sắm", "chi"), ("lazada", "Mua sắm", "chi"), ("tiki", "Mua sắm", "chi"),
                ("tiktok shop", "Mua sắm", "chi"), ("chợ", "Mua sắm", "chi"), ("siêu thị", "Mua sắm", "chi"),
                ("quần", "Mua sắm", "chi"), ("áo", "Mua sắm", "chi"), ("quần áo", "Mua sắm", "chi"),
                ("giày", "Mua sắm", "chi"), ("dép", "Mua sắm", "chi"), ("giày dép", "Mua sắm", "chi"),
                ("mũ", "Mua sắm", "chi"), ("nón", "Mua sắm", "chi"), ("kính", "Mua sắm", "chi"),
                ("váy", "Mua sắm", "chi"), ("đầm", "Mua sắm", "chi"), ("túi xách", "Mua sắm", "chi"),
                ("ví", "Mua sắm", "chi"), ("điện thoại", "Mua sắm", "chi"), ("laptop", "Mua sắm", "chi"),
                ("tai nghe", "Mua sắm", "chi"), ("phụ kiện", "Mua sắm", "chi"), ("ốp lưng", "Mua sắm", "chi"),
                ("sạc", "Mua sắm", "chi"), ("máy tính", "Mua sắm", "chi"), ("đồng hồ", "Mua sắm", "chi"),
                ("mỹ phẩm", "Mua sắm", "chi"), ("son", "Mua sắm", "chi"), ("dầu gội", "Mua sắm", "chi"),
                ("sữa tắm", "Mua sắm", "chi"), ("bột giặt", "Mua sắm", "chi"), ("đồ gia dụng", "Mua sắm", "chi"),
                ("decor", "Mua sắm", "chi"), ("trang trí", "Mua sắm", "chi"), ("nội thất", "Mua sắm", "chi"),
                ("đồ chơi", "Mua sắm", "chi"), ("quà tặng", "Mua sắm", "chi"), ("quà sinh nhật", "Mua sắm", "chi"),
                
                # --- HỌC TẬP (chi) ---
                ("học", "Học tập", "chi"), ("học tập", "Học tập", "chi"), ("sách", "Học tập", "chi"),
                ("vở", "Học tập", "chi"), ("sách vở", "Học tập", "chi"), ("bút", "Học tập", "chi"),
                ("cặp", "Học tập", "chi"), ("balo", "Học tập", "chi"), ("học phí", "Học tập", "chi"),
                ("đóng học", "Học tập", "chi"), ("tiền học", "Học tập", "chi"), ("khóa học", "Học tập", "chi"),
                ("khoá học", "Học tập", "chi"), ("học thêm", "Học tập", "chi"), ("học tiếng anh", "Học tập", "chi"),
                ("tài liệu", "Học tập", "chi"), ("văn phòng phẩm", "Học tập", "chi"),
                
                # --- LƯƠNG (thu) ---
                ("lương", "Lương", "thu"), ("nhận lương", "Lương", "thu"), ("thưởng", "Lương", "thu"),
                ("tiền công", "Lương", "thu"), ("thu nhập", "Lương", "thu"), ("lương tháng", "Lương", "thu"),
                ("làm thêm", "Lương", "thu"), ("parttime", "Lương", "thu"), ("freelance", "Lương", "thu"),
                ("hoa hồng", "Lương", "thu"), ("tiền túi", "Lương", "thu"), ("được cho", "Lương", "thu"),
                ("cho tiền", "Lương", "thu"), ("ba mẹ cho", "Lương", "thu"), ("bố mẹ cho", "Lương", "thu"),
                ("tiền tiêu vặt", "Lương", "thu"), ("bán đồ", "Lương", "thu"), ("thanh lý", "Lương", "thu"),
                ("thu nợ", "Lương", "thu"), ("đòi nợ", "Lương", "thu"), ("tiền lãi", "Lương", "thu"),
                ("cổ tức", "Lương", "thu"), ("hoàn tiền", "Lương", "thu"), ("trúng thưởng", "Lương", "thu")
            ]
            cursor.executemany("INSERT INTO keywords_mapping (keyword, category, type) VALUES (?, ?, ?)", default_keywords)
            
        conn.commit()
        logging.info("Bảng thu_chi_logs, ngan_sach và keywords_mapping đã sẵn sàng hoạt động.") 
    except Exception as e:
        logging.error(f"Lỗi khi khởi tạo database: {e}")
    finally:
        conn.close()

def insert_giao_dich(transaction_type: str, amount: float, category: str, description: Optional[str] = "", created_at: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not created_at:
            vn_time = datetime.now(VIETNAM_TZ)
            created_at = vn_time.strftime("%Y-%m-%d %H:%M:%S")
            
        sql = "INSERT INTO thu_chi_logs (type, amount, category, description, created_at) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(sql, (transaction_type, amount, category, description, created_at))
        conn.commit()
        
        last_id = cursor.lastrowid
        logging.info(f"Đã lưu thành công giao dịch ID #{last_id} vào DB lúc {created_at}.")
        return last_id
    except Exception as e:
        logging.error(f"Lỗi khi insert dữ liệu: {e}")
        raise e
    finally:
        conn.close()

def get_date_range(time_range: str) -> Optional[Tuple[str, str]]:
    """Tính toán khoảng thời gian start và end cho truy vấn theo múi giờ Việt Nam"""
    vn_now = datetime.now(VIETNAM_TZ)
    
    if time_range == "today":
        start = vn_now.strftime("%Y-%m-%d 00:00:00")
        end = vn_now.strftime("%Y-%m-%d 23:59:59")
        return start, end
    elif time_range == "yesterday":
        yesterday = vn_now - timedelta(days=1)
        start = yesterday.strftime("%Y-%m-%d 00:00:00")
        end = yesterday.strftime("%Y-%m-%d 23:59:59")
        return start, end
    elif time_range == "this_week":
        # Thứ Hai là ngày đầu tuần
        monday = vn_now - timedelta(days=vn_now.weekday())
        start = monday.strftime("%Y-%m-%d 00:00:00")
        end = vn_now.strftime("%Y-%m-%d 23:59:59")
        return start, end
    elif time_range == "this_month":
        start = vn_now.strftime("%Y-%m-01 00:00:00")
        end = vn_now.strftime("%Y-%m-%d 23:59:59")
        return start, end
    return None

def query_giao_dich(
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    time_range: str = "today",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Truy vấn các giao dịch từ DB theo bộ lọc"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT id, type, amount, category, description, created_at FROM thu_chi_logs WHERE 1=1"
        params = []
        
        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type)
            
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
            
        date_range = get_date_range(time_range)
        if date_range:
            start, end = date_range
            query += " AND created_at BETWEEN ? AND ?"
            params.extend([start, end])
            
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "type": row[1],
                "amount": row[2],
                "category": row[3],
                "description": row[4] or "",
                "created_at": row[5]
            })
        return results
    except Exception as e:
        logging.error(f"Lỗi khi truy vấn giao dịch: {e}")
        raise e
    finally:
        conn.close()

def update_giao_dich(
    transaction_id: int = -1,
    transaction_type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None
) -> bool:
    """Cập nhật thông tin giao dịch. Nếu transaction_id = -1, cập nhật giao dịch gần nhất."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if transaction_id == -1:
            cursor.execute("SELECT id FROM thu_chi_logs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                logging.warning("Không có giao dịch nào để cập nhật.")
                return False
            transaction_id = row[0]
            
        # Kiểm tra xem giao dịch có tồn tại không
        cursor.execute("SELECT id FROM thu_chi_logs WHERE id = ?", (transaction_id,))
        if not cursor.fetchone():
            logging.warning(f"Không tìm thấy giao dịch ID #{transaction_id} để cập nhật.")
            return False
            
        updates = []
        params = []
        
        if transaction_type is not None:
            updates.append("type = ?")
            params.append(transaction_type)
        if amount is not None:
            updates.append("amount = ?")
            params.append(amount)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
            
        if not updates:
            return True
            
        sql = f"UPDATE thu_chi_logs SET {', '.join(updates)} WHERE id = ?"
        params.append(transaction_id)
        
        cursor.execute(sql, params)
        conn.commit()
        logging.info(f"Đã cập nhật thành công giao dịch ID #{transaction_id}.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật giao dịch: {e}")
        raise e
    finally:
        conn.close()

def get_summary() -> dict:
    """Lấy tổng thu và tổng chi từ DB"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SUM(amount) FROM thu_chi_logs WHERE type='thu'")
        tong_thu = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(amount) FROM thu_chi_logs WHERE type='chi'")
        tong_chi = cursor.fetchone()[0] or 0.0
        
        return {"tong_thu": tong_thu, "tong_chi": tong_chi}
    except Exception as e:
        logging.error(f"Lỗi khi thống kê: {e}")
        raise e
    finally:
        conn.close()

def delete_last_transaction() -> bool:
    """Xóa giao dịch gần nhất vừa được thêm vào (Chức năng Undo)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM thu_chi_logs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return False
        
        last_id = row[0]
        cursor.execute("DELETE FROM thu_chi_logs WHERE id=?", (last_id,))
        conn.commit()
        logging.info(f"Đã xóa hoàn tác giao dịch ID #{last_id}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi xóa giao dịch: {e}")
        raise e
    finally:
        conn.close()

def delete_giao_dich_by_id(tx_id: int) -> bool:
    """Xóa giao dịch theo ID cụ thể"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM thu_chi_logs WHERE id=?", (tx_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Lỗi khi xóa giao dịch ID #{tx_id}: {e}")
        raise e
    finally:
        conn.close()

def delete_all_transactions() -> bool:
    """Xóa toàn bộ giao dịch trong bảng thu_chi_logs"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM thu_chi_logs")
        conn.commit()
        logging.info("Đã xóa toàn bộ lịch sử giao dịch thành công.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi xóa toàn bộ giao dịch: {e}")
        raise e
    finally:
        conn.close()

def delete_giao_dich_by_matching(
    transaction_type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None
) -> List[int]:
    """Tìm và xóa các giao dịch khớp với tiêu chí, trả về danh sách ID đã xóa"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT id FROM thu_chi_logs WHERE 1=1"
        params = []
        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type)
        if amount:
            query += " AND amount = ?"
            params.append(amount)
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        if not rows:
            return []
            
        ids = [row[0] for row in rows]
        # Xóa các id này
        placeholders = ",".join(["?"] * len(ids))
        cursor.execute(f"DELETE FROM thu_chi_logs WHERE id IN ({placeholders})", ids)
        conn.commit()
        logging.info(f"Đã xóa các giao dịch khớp tiêu chí có ID: {ids}")
        return ids
    except Exception as e:
        logging.error(f"Lỗi khi xóa giao dịch theo bộ lọc: {e}")
        raise e
    finally:
        conn.close()

STANDARD_CATEGORIES_MAP = {
    "an uong": "Ăn uống",
    "ăn uống": "Ăn uống",
    "di chuyen": "Di chuyển",
    "di chuyển": "Di chuyển",
    "hoc tap": "Học tập",
    "học tập": "Học tập",
    "mua sam": "Mua sắm",
    "mua sắm": "Mua sắm",
    "luong": "Lương",
    "lương": "Lương",
    "khac": "Khác",
    "khác": "Khác"
}

def normalize_category_name(cat: str) -> str:
    if not cat:
        return "Khác"
    c_strip = cat.strip()
    c_lower = c_strip.lower()
    if c_lower in STANDARD_CATEGORIES_MAP:
        return STANDARD_CATEGORIES_MAP[c_lower]
    return c_strip[0].upper() + c_strip[1:] if len(c_strip) > 0 else c_strip

def delete_ngan_sach(category: str) -> bool:
    """Xóa ngân sách hạn mức của một danh mục (không phân biệt hoa thường)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        norm_cat = normalize_category_name(category)
        cursor.execute("DELETE FROM ngan_sach WHERE LOWER(category) = LOWER(?) OR LOWER(category) = LOWER(?)", (category.strip(), norm_cat))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Lỗi khi xóa ngân sách {category}: {e}")
        raise e
    finally:
        conn.close()

def set_ngan_sach(category: str, amount: float) -> None:
    """Thiết lập hoặc cập nhật hạn mức chi tiêu hàng tháng cho một danh mục (Cập nhật đúng bản ghi cũ nếu đã có)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        norm_cat = normalize_category_name(category)
        
        # Tìm danh mục khớp nhất trong DB hiện tại
        cursor.execute("SELECT category FROM ngan_sach")
        rows = cursor.fetchall()
        target_cat = norm_cat
        for (existing_cat,) in rows:
            if existing_cat.lower().strip() == category.lower().strip() or is_category_match(existing_cat, norm_cat):
                target_cat = existing_cat
                break

        # Xóa các bản ghi trùng lặp không phân biệt hoa thường trước khi insert
        cursor.execute("DELETE FROM ngan_sach WHERE LOWER(category) = LOWER(?) OR LOWER(category) = LOWER(?)", (category.strip(), target_cat.strip()))
        cursor.execute(
            "INSERT INTO ngan_sach (category, amount) VALUES (?, ?)",
            (target_cat, amount)
        )
        conn.commit()
        logging.info(f"Đã thiết lập hạn mức {amount}đ cho danh mục {target_cat}.")
    except Exception as e:
        logging.error(f"Lỗi khi thiết lập ngân sách: {e}")
        raise e
    finally:
        conn.close()

def get_ngan_sach(category: str) -> Optional[float]:
    """Lấy hạn mức ngân sách của một danh mục"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        norm_cat = normalize_category_name(category)
        cursor.execute("SELECT amount FROM ngan_sach WHERE LOWER(category) = LOWER(?) OR LOWER(category) = LOWER(?)", (category.strip(), norm_cat))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Lỗi khi lấy ngân sách: {e}")
        raise e
    finally:
        conn.close()


def get_all_ngan_sach() -> List[Dict[str, Any]]:
    """Lấy tất cả hạn mức ngân sách đã thiết lập"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT category, amount FROM ngan_sach")
        rows = cursor.fetchall()
        return [{"category": row[0], "amount": row[1]} for row in rows]
    except Exception as e:
        logging.error(f"Lỗi khi lấy danh sách ngân sách: {e}")
        raise e
    finally:
        conn.close()

def is_category_match(cat1: str, cat2: str) -> bool:
    """
    Kiểm tra xem hai danh mục có THỰC SỰ liên quan đến nhau không.
    Ưu tiên khớp chính xác, sau đó khớp chứa nhau, cuối cùng mới dùng từ chung.
    
    Quy tắc an toàn:
    - "Đi chơi" vs "Đi ăn"  → False ✅ (chỉ chung "đi" – quá ngắn/chung chung)
    - "Đi chơi" vs "Đi chơi Đà Lạt" → True ✅ (chuỗi chứa nhau)
    - "Ăn uống" vs "Ăn vặt" → False ✅ (không có từ nội dung chung ≥4 ký tự)
    - "Sức khỏe" vs "Chăm sóc sức khỏe" → True ✅ (chứa "sức khỏe")
    """
    c1 = cat1.lower().strip()
    c2 = cat2.lower().strip()
    
    # 1. Khớp chính xác (không phân biệt hoa thường)
    if c1 == c2:
        return True
    
    # 2. Một chuỗi chứa đầy đủ chuỗi kia (e.g. "Ăn uống" chứa trong "Chi phí ăn uống")
    if c1 in c2 or c2 in c1:
        return True

    # 3. Từ chung có nghĩa:
    # - Các từ quá ngắn/chung chung bị loại (len < 4 hoặc nằm trong weak_words)
    # - "đi", "ăn", "mua", "chi", "thu", "và", "cho" → loại bỏ
    weak_words = {
        # Giới từ, liên từ
        "và", "cho", "của", "tại", "ở", "bằng", "với", "các", "những", "để",
        # Động từ phổ biến, dễ nhầm giữa các danh mục
        "đi", "ăn", "mua", "chi", "thu", "có", "là", "làm", "dùng", "tiêu",
        # Từ ngắn < 3 ký tự sẽ bị loại qua len check bên dưới
    }
    
    words1 = {w for w in c1.split() if w not in weak_words and len(w) >= 4}
    words2 = {w for w in c2.split() if w not in weak_words and len(w) >= 4}
    
    # Chỉ khớp khi có ít nhất 1 từ nội dung ý nghĩa chung
    if words1 and words2 and bool(words1 & words2):
        return True
    
    return False


def find_matching_budget(category: str) -> Optional[Tuple[str, float]]:
    """Tìm hạn mức chi tiêu khớp nhất với danh mục chi tiêu"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT category, amount FROM ngan_sach")
        rows = cursor.fetchall()
        
        # Khớp chính xác trước
        for row_cat, amount in rows:
            if row_cat.lower() == category.lower():
                return row_cat, amount
                
        # Khớp tương đối
        for row_cat, amount in rows:
            if is_category_match(row_cat, category):
                return row_cat, amount
                
        return None
    except Exception as e:
        logging.error(f"Lỗi tìm hạn mức khớp: {e}")
        return None
    finally:
        conn.close()

def get_monthly_spending_for_budget_category(budget_cat: str) -> float:
    """Tính tổng chi tiêu trong tháng hiện tại khớp với danh mục ngân sách"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        date_range = get_date_range("this_month")
        if not date_range:
            return 0.0
        start, end = date_range
        
        # Lấy tất cả giao dịch chi tiêu trong tháng
        cursor.execute(
            "SELECT category, amount FROM thu_chi_logs WHERE type = 'chi' AND created_at BETWEEN ? AND ?",
            (start, end)
        )
        rows = cursor.fetchall()
        
        total = 0.0
        for tx_cat, amount in rows:
            # So sánh đối sánh tương đối dùng helper is_category_match
            if is_category_match(budget_cat, tx_cat):
                total += amount
        return total
    except Exception as e:
        logging.error(f"Lỗi tính tổng chi tiêu tháng theo ngân sách: {e}")
        raise e
    finally:
        conn.close()

def get_keyword_mappings() -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả từ khóa phân loại"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, keyword, category, type FROM keywords_mapping ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "keyword": r[1], "category": r[2], "type": r[3]} for r in rows]
    except Exception as e:
        logging.error(f"Lỗi khi lấy từ khóa: {e}")
        return []
    finally:
        conn.close()

def add_keyword_mapping(keyword: str, category: str, transaction_type: str) -> int:
    """Thêm hoặc cập nhật một từ khóa phân loại"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO keywords_mapping (keyword, category, type) VALUES (?, ?, ?)",
            (keyword.strip().lower(), category, transaction_type)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logging.error(f"Lỗi khi thêm từ khóa: {e}")
        raise e
    finally:
        conn.close()

def delete_keyword_mapping(mapping_id: int) -> bool:
    """Xóa một từ khóa phân loại theo ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM keywords_mapping WHERE id = ?", (mapping_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Lỗi khi xóa từ khóa: {e}")
        raise e
    finally:
        conn.close()

def update_keyword_mapping(mapping_id: int, keyword: str, category: str, transaction_type: str) -> bool:
    """Cập nhật thông tin của một từ khóa phân loại theo ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE keywords_mapping SET keyword = ?, category = ?, type = ? WHERE id = ?",
            (keyword.strip().lower(), category, transaction_type, mapping_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật từ khóa: {e}")
        raise e
    finally:
        conn.close()

def get_all_categories() -> List[str]:
    """Lấy danh sách tất cả các danh mục độc nhất từ keywords_mapping, ngan_sach và thu_chi_logs"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        categories = set(["Ăn uống", "Di chuyển", "Học tập", "Mua sắm", "Lương", "Khác"])
        cursor.execute("SELECT DISTINCT category FROM keywords_mapping")
        for row in cursor.fetchall():
            if row[0]:
                categories.add(row[0].strip())
        cursor.execute("SELECT DISTINCT category FROM ngan_sach")
        for row in cursor.fetchall():
            if row[0]:
                categories.add(row[0].strip())
        cursor.execute("SELECT DISTINCT category FROM thu_chi_logs")
        for row in cursor.fetchall():
            if row[0]:
                categories.add(row[0].strip())
        return sorted(list(categories))
    except Exception as e:
        logging.error(f"Lỗi khi lấy danh sách danh mục: {e}")
        return ["Ăn uống", "Di chuyển", "Học tập", "Mua sắm", "Lương", "Khác"]
    finally:
        conn.close()
