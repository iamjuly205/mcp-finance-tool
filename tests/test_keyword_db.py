# tests/test_keyword_db.py
import pytest
import os
import sqlite3
import database

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    # Sử dụng db tạm thời cho việc test
    test_db_path = tmp_path / "test_keyword_finance.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_keyword_table_initialization_and_crud():
    # Verify default seeding is done
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keywords_mapping")
    count = cursor.fetchone()[0]
    assert count > 0, "Seeding failed: keyword table is empty."
    
    # Test adding a custom mapping
    mapping_id = database.add_keyword_mapping("bún đậu", "Ăn uống", "chi")
    assert mapping_id > 0
    
    # Test querying
    mappings = database.get_keyword_mappings()
    keywords = [m["keyword"] for m in mappings]
    assert "bún đậu" in keywords
    
    # Test update
    success_update = database.update_keyword_mapping(mapping_id, "bún đậu mắm tôm", "Ăn uống", "chi")
    assert success_update is True
    
    # Test delete
    success_delete = database.delete_keyword_mapping(mapping_id)
    assert success_delete is True
