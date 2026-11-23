from typing import Optional

ESCAPE_CHAR = "\\"


def normalize_keyword(raw: Optional[str]) -> Optional[str]:
    """
    Chuẩn hoá keyword tìm kiếm theo quy tắc:
    1. trim() khoảng trắng đầu/cuối.
    2. Nếu rỗng hoặc toàn whitespace -> trả về None (bỏ filter).
    """
    if raw is None:
        return None
    trimmed = raw.strip()
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
    Tạo pattern '%escaped_lower%' cho truy vấn LIKE với ESCAPE '\\' không phân biệt hoa/thường.
    """
    escaped = escape_like_literal(keyword.lower())
    return f"%{escaped}%"
