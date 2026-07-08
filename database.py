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
        conn.commit()
        logging.info("Bảng thu_chi_logs và ngan_sach đã sẵn sàng hoạt động.") 
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

def set_ngan_sach(category: str, amount: float) -> None:
    """Thiết lập hoặc cập nhật hạn mức chi tiêu hàng tháng cho một danh mục"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO ngan_sach (category, amount) VALUES (?, ?)",
            (category, amount)
        )
        conn.commit()
        logging.info(f"Đã thiết lập hạn mức {amount}đ cho danh mục {category}.")
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
        cursor.execute("SELECT amount FROM ngan_sach WHERE category = ?", (category,))
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
    """Kiểm tra xem hai danh mục có liên quan đến nhau hay không (khớp từ hoặc chứa nhau)"""
    c1 = cat1.lower().strip()
    c2 = cat2.lower().strip()
    if c1 == c2 or c1 in c2 or c2 in c1:
        return True
    
    stop_words = {"và", "cho", "của", "tại", "ở", "bằng", "với", "các", "những", "để"}
    words1 = {w for w in c1.split() if w not in stop_words and len(w) >= 2}
    words2 = {w for w in c2.split() if w not in stop_words and len(w) >= 2}
    return bool(words1 & words2)

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