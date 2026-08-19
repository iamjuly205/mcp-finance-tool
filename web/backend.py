# web/backend.py
import sys
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

# Thêm thư mục gốc vào path để import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database
import server
from web.gemini_parser import parse_intent_with_gemini, parse_with_gemini
from web.keyword_parser import route_intent_with_keywords, parse_with_keywords, extract_amount, detect_category, remove_accents as kp_remove_accents

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

app = FastAPI(title="Xiaozhi Finance Web API")

class TransactionCreate(BaseModel):
    transaction_type: str
    amount: float
    category: str
    description: Optional[str] = ""

class BudgetCreate(BaseModel):
    category: str
    amount: float

class KeywordMappingCreate(BaseModel):
    keyword: str
    category: str
    type: str  # "thu" or "chi"

class ChatInput(BaseModel):
    message: str

# Khởi tạo db khi bắt đầu
@app.on_event("startup")
def startup_db():
    database.init_db()

@app.get("/api/mcp-status")
def get_mcp_status_api():
    import json
    import time
    status_file = "mcp_status.json"
    if not os.path.exists(status_file):
        return {"status": "offline", "message": "Bridge chưa chạy"}
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check if timestamp is within last 12 seconds
        if time.time() - data.get("timestamp", 0) > 12:
            return {"status": "offline", "message": "Bridge mất kết nối (stale)"}
        return {"status": data.get("status", "offline")}
    except Exception as e:
        return {"status": "offline", "message": str(e)}

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
                spent_str = f"{int(spent_amount):,}".replace(",", ".")
                limit_str = f"{int(budget_amount):,}".replace(",", ".")
                if spent_amount > budget_amount:
                    warning = f"Cảnh báo: Bạn đã chi tiêu vượt hạn mức của danh mục '{budget_cat}' ({spent_str}/{limit_str} đồng)!"
                elif spent_amount >= budget_amount * 0.8:
                    percent = int((spent_amount / budget_amount) * 100)
                    warning = f"Cảnh báo: Chi tiêu cho '{budget_cat}' đã đạt {percent}% hạn mức tháng ({spent_str}/{limit_str} đồng)!"
                    
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

@app.delete("/api/transactions/{tx_id}")
def delete_transaction_by_id_api(tx_id: int):
    try:
        success = database.delete_giao_dich_by_id(tx_id)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")
        return {"success": True, "message": "Xóa giao dịch thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions")
def delete_all_transactions_api():
    try:
        success = database.delete_all_transactions()
        return {"success": success, "message": "Đã xóa toàn bộ lịch sử giao dịch thành công."}
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

@app.delete("/api/budgets/{category}")
def delete_budget_api(category: str):
    try:
        success = database.delete_ngan_sach(category)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy hạn mức ngân sách.")
        return {"success": True, "message": f"Đã xóa hạn mức ngân sách {category}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords")
def get_keywords_api():
    try:
        return database.get_keyword_mappings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keywords")
def add_keyword_api(mapping: KeywordMappingCreate):
    if not mapping.keyword.strip():
        raise HTTPException(status_code=400, detail="Từ khóa không được để trống.")
    if mapping.type not in ["thu", "chi"]:
        raise HTTPException(status_code=400, detail="Loại giao dịch phải là 'thu' hoặc 'chi'.")
    try:
        mapping_id = database.add_keyword_mapping(mapping.keyword, mapping.category, mapping.type)
        return {"success": True, "id": mapping_id, "message": "Thêm từ khóa thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/keywords/{mapping_id}")
def delete_keyword_api(mapping_id: int):
    try:
        success = database.delete_keyword_mapping(mapping_id)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy từ khóa.")
        return {"success": True, "message": "Xóa từ khóa thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/keywords/{mapping_id}")
def update_keyword_api(mapping_id: int, mapping: KeywordMappingCreate):
    try:
        success = database.update_keyword_mapping(mapping_id, mapping.keyword, mapping.category, mapping.type)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy từ khóa.")
        return {"success": True, "message": "Cập nhật từ khóa thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def simulate_chat_api(chat: ChatInput):
    msg = chat.message.strip()
    
    try:
        source = None
        
        def write_routing_log(message: str):
            try:
                from datetime import datetime
                with open("server.log", "a", encoding="utf-8") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                    f.write(f"{timestamp} - INFO - {message}\n")
            except Exception:
                pass

        # 1. Thử định tuyến bằng bộ từ khóa cục bộ trước (Keyword-First)
        parsed = route_intent_with_keywords(msg)
        if parsed:
            source = "keyword"
            print(f"\n>>> [CHỌN ĐƯỜNG TRUYỀN] Câu lệnh: \"{msg}\"", flush=True)
            print(">>> KẾT QUẢ: Khớp bộ từ khóa cục bộ (SYSTEM KEYWORDS) thành công!\n", flush=True)
            write_routing_log(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Định tuyến bằng: SYSTEM KEYWORD (Cục bộ)")
            logging.info(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Định tuyến bằng: SYSTEM KEYWORD (Cục bộ)")
        
        # 2. Nếu không khớp từ khóa, fallback sang Gemini (LLM)
        learned_keywords = []
        if not parsed:
            llm_result = parse_intent_with_gemini(msg)
            if llm_result:
                parsed = llm_result
                source = "llm"
                learned_keywords = llm_result.get("learned_keywords", [])
                print(f"\n>>> [CHỌN ĐƯỜNG TRUYỀN] Câu lệnh: \"{msg}\"", flush=True)
                print(">>> KẾT QUẢ: Sử dụng GEMINI API (LLM) thành công!", flush=True)
                if learned_keywords:
                    print(f">>> 🧠 HỆ THỐNG ĐÃ HỌC: {learned_keywords} → danh mục '{parsed['arguments'].get('category', '?')}'\n", flush=True)
                    write_routing_log(f"[SELF-LEARN] Học keyword(s): {learned_keywords} → '{parsed['arguments'].get('category', '?')}'")
                else:
                    print("", flush=True)
                write_routing_log(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Định tuyến bằng: GEMINI API (LLM)")
                logging.info(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Định tuyến bằng: GEMINI API (LLM)")

            
        # 3. Không nhận diện được (Keyword và LLM đều không xử lý được)
        if not parsed:
            print(f"\n>>> [CHỌN ĐƯỜNG TRUYỀN] Câu lệnh: \"{msg}\"", flush=True)
            print(">>> KẾT QUẢ: Không tìm thấy phương thức định tuyến phù hợp!\n", flush=True)
            write_routing_log(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Không nhận diện được!")
            logging.warning(f"[CHAT ROUTING] Câu lệnh: '{msg}' -> Không nhận diện được!")
            return {
                "tts": "Xin lỗi, tôi chưa nhận diện được yêu cầu của bạn. Bạn có thể thử lại bằng câu nói khác rõ hơn không?",
                "source": "none",
                "rpc_call": None,
                "rpc_response": None
            }

                
        # 4. Thực thi công cụ đã được xác định
        if parsed:
            tool_name = parsed["tool"]
            arguments = parsed["arguments"]
            
            # Gọi trực tiếp logic của server.py
            if tool_name == "ghi_nhan_thu_chi":
                tts_response = server.ghi_nhan_thu_chi(
                    transaction_type=arguments.get("transaction_type", "chi"),
                    amount=float(arguments.get("amount", 0)),
                    category=arguments.get("category", "Khác"),
                    description=arguments.get("description", "")
                )
            elif tool_name == "thong_ke_thu_chi":
                tts_response = server.thong_ke_thu_chi()
            elif tool_name == "huy_giao_dich_gan_nhat":
                tts_response = server.huy_giao_dich_gan_nhat()
            elif tool_name == "xem_ngan_sach":
                tts_response = server.xem_ngan_sach()
            elif tool_name == "thiet_lap_han_muc":
                tts_response = server.thiet_lap_han_muc(
                    category=arguments.get("category", "Khác"),
                    amount=float(arguments.get("amount", 0))
                )
            elif tool_name == "sua_giao_dich":
                tts_response = server.sua_giao_dich(
                    transaction_id=int(arguments.get("transaction_id", -1)),
                    transaction_type=arguments.get("transaction_type"),
                    amount=float(arguments.get("amount")) if arguments.get("amount") is not None else None,
                    category=arguments.get("category"),
                    description=arguments.get("description")
                )
            elif tool_name == "truy_van_giao_dich":
                tts_response = server.truy_van_giao_dich(
                    transaction_type=arguments.get("transaction_type"),
                    category=arguments.get("category"),
                    time_range=arguments.get("time_range", "today"),
                    limit=int(arguments.get("limit", 10))
                )
            else:
                raise ValueError(f"Không nhận dạng được công cụ {tool_name}")
                
            # Tạo gói phản hồi JSON-RPC 2.0 mock để giả lập robot console
            json_rpc_call = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
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
                "source": source,
                "learned_keywords": learned_keywords,
                "rpc_call": json_rpc_call,
                "rpc_response": json_rpc_response
            }
        else:
            return {
                "tts": "Robot Xiaozhi không nhận diện được ý định của bạn. Hãy nói rõ ràng hơn, ví dụ: 'Ăn phở hết 50k' hoặc 'báo cáo thống kê tài chính'.",
                "rpc_call": None,
                "rpc_response": None
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount thư mục static (đặt cuối cùng để tránh chặn đứng các route API)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
