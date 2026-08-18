# reseed_keywords.py
import sqlite3
import database

def reseed():
    print("Connecting to database...")
    conn = sqlite3.connect("quan_ly_thu_chi.db")
    cursor = conn.cursor()
    
    print("Clearing current keywords table...")
    cursor.execute("DELETE FROM keywords_mapping")
    conn.commit()
    conn.close()
    
    print("Seeding new expanded keywords list...")
    database.init_db()
    print("Reseed completed successfully!")

if __name__ == "__main__":
    reseed()
