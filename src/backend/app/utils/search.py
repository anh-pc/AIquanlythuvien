import unicodedata
from typing import Optional

ESCAPE_CHAR = "\\"


def unicode_casefold(value: Optional[str]) -> Optional[str]:
    """
    Chuẩn hoá chuỗi về Unicode NFC và hạ chữ bằng casefold()
    để so khớp chính xác mọi ký tự tiếng Việt có dấu (Đ/đ, Ă/ă, Ơ/ơ, Ư/ư...).
    """
    if value is None:
        return None
    normalized = unicodedata.normalize("NFC", str(value))
    return normalized.casefold()


def normalize_keyword(raw: Optional[str]) -> Optional[str]:
    """
    Chuẩn hoá keyword tìm kiếm theo quy tắc:
    1. Chuẩn hoá Unicode NFC.
    2. trim() khoảng trắng đầu/cuối.
    3. Nếu rỗng hoặc toàn whitespace -> trả về None (bỏ filter).
    """
    if raw is None:
        return None
    nfc = unicodedata.normalize("NFC", str(raw))
    trimmed = nfc.strip()
    if not trimmed:
        return None
    return trimmed


def escape_like_literal(keyword: str) -> str:
    """
    Escape các ký tự đặc biệt của SQL LIKE (\\, %, _) để tìm đúng nghĩa literal.
    """
    return (
        keyword.replace(ESCAPE_CHAR, ESCAPE_CHAR + ESCAPE_CHAR)
        .replace("%", ESCAPE_CHAR + "%")
        .replace("_", ESCAPE_CHAR + "_")
    )


def build_like_pattern(keyword: str) -> str:
    """
    Tạo pattern '%escaped_casefold%' cho truy vấn LIKE với ESCAPE '\\'
    không phân biệt hoa/thường kể cả tiếng Việt có dấu.
    """
    folded = unicode_casefold(keyword) or ""
    escaped = escape_like_literal(folded)
    return f"%{escaped}%"
