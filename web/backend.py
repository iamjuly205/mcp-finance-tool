# web/backend.py
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

# Thêm thư mục gốc vào path để import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
from web.gemini_parser import parse_with_gemini

def remove_accents(input_str: str) -> str:
    s1 = 'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỊịỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
    s0 = 'AAAAEECIIOOOOUUYaaaaeecioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
    res = []
    for c in input_str:
        idx = s1.find(c)
        if idx != -1:
            res.append(s0[idx])
        else:
            res.append(c)
    return "".join(res)

app = FastAPI(title="Xiaozhi Finance Web API")

class TransactionCreate(BaseModel):
    transaction_type: str
    amount: float
    category: str
    description: Optional[str] = ""

class BudgetCreate(BaseModel):
    category: str
    amount: float

class ChatInput(BaseModel):
    message: str

# Khởi tạo db khi bắt đầu
@app.on_event("startup")
def startup_db():
    database.init_db()

@app.get("/api/summary")
def get_summary_api():
    try:
        return database.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def get_transactions_api(
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    time_range: str = "this_month",
    limit: int = 50
):
    try:
        return database.query_giao_dich(transaction_type, category, time_range, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions")
def create_transaction_api(tx: TransactionCreate):
    if tx.transaction_type not in ["thu", "chi"]:
        raise HTTPException(status_code=400, detail="Loại giao dịch phải là 'thu' hoặc 'chi'.")
    if tx.amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền phải lớn hơn 0.")
    try:
        tx_id = database.insert_giao_dich(
            transaction_type=tx.transaction_type,
            amount=tx.amount,
            category=tx.category,
            description=tx.description
        )
        
        # Kiểm tra ngân sách cảnh báo
        warning = None
        if tx.transaction_type == "chi":
            match = database.find_matching_budget(tx.category)
            if match:
                budget_cat, budget_amount = match
                spent_amount = database.get_monthly_spending_for_budget_category(budget_cat)
                if spent_amount > budget_amount:
                    warning = f"Cảnh báo vượt hạn mức ngân sách '{budget_cat}'!"
                elif spent_amount >= budget_amount * 0.8:
                    percent = int((spent_amount / budget_amount) * 100)
                    warning = f"Cảnh báo: Ngân sách '{budget_cat}' đạt {percent}% hạn mức."
                    
        return {
            "success": True, 
            "id": tx_id, 
            "warning": warning, 
            "message": f"Ghi nhận {tx.transaction_type} {tx.amount}đ thành công."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/last")
def delete_last_transaction_api():
    try:
        success = database.delete_last_transaction()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets")
def get_budgets_api():
    try:
        budgets = database.get_all_ngan_sach()
        detailed_budgets = []
        for b in budgets:
            cat = b["category"]
            limit_amount = b["amount"]
            spent = database.get_monthly_spending_for_budget_category(cat)
            detailed_budgets.append({
                "category": cat,
                "limit": limit_amount,
                "spent": spent,
                "remaining": max(0.0, limit_amount - spent),
                "over": max(0.0, spent - limit_amount),
                "percentage": min(100, int((spent / limit_amount) * 100)) if limit_amount > 0 else 0
            })
        return detailed_budgets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/budgets")
def set_budget_api(budget: BudgetCreate):
    if budget.amount <= 0:
        raise HTTPException(status_code=400, detail="Hạn mức phải lớn hơn 0.")
    try:
        database.set_ngan_sach(budget.category, budget.amount)
        return {"success": True, "message": f"Đặt hạn mức {budget.amount}đ cho {budget.category} thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def simulate_chat_api(chat: ChatInput):
    msg = chat.message.strip()
    
    try:
        # Thử phân tích cú pháp bằng Gemini trước
        parsed = parse_with_gemini(msg)
        
        if parsed:
            tx_type = parsed["transaction_type"]
            amount = parsed["amount"]
            category = parsed["category"]
            description = parsed["description"]
        else:
            # Sử dụng bộ phân tích Regex làm dự phòng nếu không có API key hoặc lỗi
            import re
            msg_lower = msg.lower()
            
            # Nhận diện số tiền (k, tr, hoặc số thường)
            amount_match = re.search(r'(\d+)\s*(k|tr|triệu|đ|dong|đồng)?', msg_lower)
            amount = 0.0
            if amount_match:
                val = float(amount_match.group(1))
                unit = amount_match.group(2)
                if unit in ['k']:
                    amount = val * 1000
                elif unit in ['tr', 'triệu']:
                    amount = val * 1000000
                else:
                    amount = val
                    
            # Nhận diện loại giao dịch
            tx_type = "chi"
            if any(w in msg_lower for w in ["thu", "lương", "nhận", "kiếm", "thưởng", "cộng"]):
                tx_type = "thu"
                
            # Nhận diện category bằng cả văn bản có dấu và không dấu
            msg_no_accent = remove_accents(msg_lower)
            category = "Khác"
            
            if any(w in msg_lower for w in ["ăn", "uống", "phở", "bánh", "cơm", "lẩu", "trưa", "sáng", "tối"]) or any(w in msg_no_accent for w in ["an", "uong", "pho", "banh", "com", "lau", "trua", "sang", "toi", "cafe"]):
                category = "Ăn uống"
            elif any(w in msg_lower for w in ["xe", "xăng", "grab", "taxi", "di chuyển", "đi lại"]) or any(w in msg_no_accent for w in ["xe", "xang", "grab", "taxi", "di chuyen", "di lai"]):
                category = "Di chuyển"
            elif any(w in msg_lower for w in ["lương", "thu nhập"]) or any(w in msg_no_accent for w in ["luong", "thu nhap"]):
                category = "Lương"
            elif any(w in msg_lower for w in ["học", "sách", "khoá học"]) or any(w in msg_no_accent for w in ["hoc", "sach", "khoa hoc"]):
                category = "Học tập"
            elif any(w in msg_lower for w in ["mua", "sắm", "shopee", "quần", "áo"]) or any(w in msg_no_accent for w in ["mua", "sam", "shopee", "quan", "ao"]):
                category = "Mua sắm"
                
            description = msg
            
        if amount > 0:
            tx_id = database.insert_giao_dich(tx_type, amount, category, description)
            spent_str = f"{int(amount):,}".replace(",", ".")
            
            # Kiểm tra ngân sách cảnh báo
            warning = ""
            if tx_type == "chi":
                match = database.find_matching_budget(category)
                if match:
                    b_cat, b_amt = match
                    spent_total = database.get_monthly_spending_for_budget_category(b_cat)
                    if spent_total > b_amt:
                        warning = f" Cảnh báo: Vượt hạn mức ngân sách {b_cat}!"
                    elif spent_total >= b_amt * 0.8:
                        warning = f" Cảnh báo: Ngân sách {b_cat} đạt {int((spent_total/b_amt)*100)}% hạn mức."
                        
            action_label = "chi tiêu" if tx_type == "chi" else "thu nhập"
            tts_response = f"Đã ghi nhận khoản {action_label} {spent_str}đ cho hạng mục {category}.{warning}"
            
            # Trả về cả JSON RPC Mock Call
            json_rpc_call = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ghi_nhan_thu_chi",
                    "arguments": {
                        "transaction_type": tx_type,
                        "amount": amount,
                        "category": category,
                        "description": description
                    }
                },
                "id": 1
            }
            json_rpc_response = {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": tts_response
                        }
                    ]
                },
                "id": 1
            }
            
            return {
                "tts": tts_response,
                "rpc_call": json_rpc_call,
                "rpc_response": json_rpc_response
            }
        else:
            return {
                "tts": "Tôi không nhận diện được số tiền trong câu nói của bạn. Hãy thử nói rõ hơn, ví dụ: 'Ăn phở hết 50k'.",
                "rpc_call": None,
                "rpc_response": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount thư mục static (đặt cuối cùng để tránh chặn đứng các route API)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
