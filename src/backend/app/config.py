from datetime import date
from typing import Callable, Optional

# Hằng số nghiệp vụ chuẩn (NV1–NV9)
LOAN_DAYS: int = 14
MAX_ACTIVE_LOANS: int = 5
MAX_RENEWALS: int = 2
RENEW_DAYS: int = 7
FINE_PER_DAY: int = 1000

DEFAULT_PAGE_SIZE: int = 10
MAX_PAGE_SIZE: int = 100

COPY_STATUS_LABELS = {
    "available": "Còn trong kho",
    "borrowed": "Đang mượn",
    "damaged": "Hư hỏng",
    "lost": "Thất lạc",
}

VALID_COPY_STATUSES = set(COPY_STATUS_LABELS.keys())
MANUAL_ALLOWED_COPY_STATUSES = {"available", "damaged", "lost"}
VALID_RETURN_CONDITIONS = {"normal", "damaged", "lost"}

# Hàm lấy ngày "Hôm nay" duy nhất để test có thể ghi đè (clock override)
_clock_override: Optional[Callable[[], date]] = None


def get_today() -> date:
    """Trả về ngày hôm nay (kiểu datetime.date). Có thể ghi đè trong test qua set_today_override()."""
    if _clock_override is not None:
        return _clock_override()
    return date.today()


def get_today_iso() -> str:
    """Trả về ngày hôm nay ở định dạng ISO YYYY-MM-DD."""
    return get_today().isoformat()


def set_today_override(fn: Optional[Callable[[], date]]) -> None:
    """Thiết lập hoặc xoá hàm ghi đè ngày hôm nay phục vụ kiểm thử tự động."""
    global _clock_override
    _clock_override = fn
