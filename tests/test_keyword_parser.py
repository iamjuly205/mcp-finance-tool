# tests/test_keyword_parser.py
import pytest
import database
from web.keyword_parser import parse_with_keywords

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db_path = tmp_path / "test_parser.db"
    original_db = database.DB_FILE
    database.DB_FILE = str(test_db_path)
    database.init_db()
    yield
    database.DB_FILE = original_db

def test_parse_with_keywords_success():
    # 1. Test "ăn trưa hết 55k" (tiếng Việt có dấu)
    res1 = parse_with_keywords("ăn trưa hết 55k")
    assert res1 is not None
    assert res1["transaction_type"] == "chi"
    assert res1["amount"] == 55000.0
    assert res1["category"] == "Ăn uống"
    assert "ăn trưa hết 55k" in res1["description"]

    # 2. Test "nhận lương 15tr" (tiếng Việt có dấu)
    res2 = parse_with_keywords("nhận lương 15tr")
    assert res2 is not None
    assert res2["transaction_type"] == "thu"
    assert res2["amount"] == 15000000.0
    assert res2["category"] == "Lương"

def test_parse_with_keywords_no_match():
    # No amount -> Should fail parsing (None) so we fallback to LLM
    assert parse_with_keywords("hôm nay ăn cơm") is None

    # Unregistered category (e.g. paying rent) -> Category becomes "Khác" -> Returns None to trigger LLM parsing
    assert parse_with_keywords("tiền nhà 3tr") is None
