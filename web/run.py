# web/run.py
import sys
import os
import uvicorn

# Thêm thư mục gốc vào PYTHONPATH để có thể import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)
