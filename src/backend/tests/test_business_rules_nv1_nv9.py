"""
Bộ kiểm thử tự động mức API Integration cho toàn bộ quy tắc nghiệp vụ NV1–NV9.
Chạy trên SQLite in-memory riêng biệt của mỗi test, không chạm DB của ứng dụng.
"""
from datetime import date, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from app.config import (
    FINE_PER_DAY,
    LOAN_DAYS,
    MAX_ACTIVE_LOANS,
    RENEW_DAYS,
    get_today,
    set_today_override,
)
from app.models import Book, BookCopy, Loan, Reader


# =====================================================================
# NV1: Mượn sách hợp lệ & các điều kiện từ chối
# =====================================================================
def test_nv1_borrow_success_updates_copy_and_sets_due_date(client, db_session):
    """NV1: Mượn hợp lệ tạo phiếu mượn, chuyển bản sao -> 'borrowed', due_date = today + 14 ngày."""
    fixed_today = date(2026, 11, 23)
    set_today_override(lambda: fixed_today)

    reader = db_session.query(Reader).filter(Reader.card_no == "DG010").first()
    available_copy = (
        db_session.query(BookCopy)
        .filter(BookCopy.status == "available")
        .first()
    )
    assert reader is not None and available_copy is not None

    res = client.post(
        "/api/loans",
        json={"reader_id": reader.id, "copy_id": available_copy.id, "note": "Mượn test NV1"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["reader_id"] == reader.id
    assert body["copy_id"] == available_copy.id
    assert body["borrowed_at"] == "2026-11-23"
    assert body["due_date"] == (fixed_today + timedelta(days=LOAN_DAYS)).isoformat()
    assert body["status"] == "borrowed"
    assert body["status_label"] == "Đang mượn"

    # Kiểm tra trạng thái bản sao đã chuyển sang 'borrowed'
    db_session.refresh(available_copy)
    assert available_copy.status == "borrowed"


def test_nv1_reject_inactive_reader_and_unavailable_copy(client, db_session):
    """NV1: Từ chối khi độc giả bị vô hiệu hoá (DG012) hoặc bản sao không ở trạng thái 'available'."""
    inactive_reader = db_session.query(Reader).filter(Reader.card_no == "DG012").first()
    avail_copy = db_session.query(BookCopy).filter(BookCopy.status == "available").first()

    # 1. Độc giả bị khoá thẻ
    res_inactive = client.post(
        "/api/loans",
        json={"reader_id": inactive_reader.id, "copy_id": avail_copy.id},
    )
    assert res_inactive.status_code == 400
    assert "vô hiệu hoá" in res_inactive.json()["detail"].lower()

    # 2. Bản sao đang hư hỏng (damaged) hoặc thất lạc (lost)
    active_reader = db_session.query(Reader).filter(Reader.card_no == "DG010").first()
    damaged_copy = db_session.query(BookCopy).filter(BookCopy.status == "damaged").first()
    res_damaged = client.post(
        "/api/loans",
        json={"reader_id": active_reader.id, "copy_id": damaged_copy.id},
    )
    assert res_damaged.status_code == 400
    assert "hư hỏng" in res_damaged.json()["detail"].lower()


def test_nv1_reject_when_reader_has_overdue_loan_or_reaches_max_5_loans(client, db_session):
    """NV1: Từ chối khi độc giả đang có phiếu quá hạn (DG004) hoặc đã mượn đủ 5 cuốn (MAX_ACTIVE_LOANS=5)."""
    avail_copies = (
        db_session.query(BookCopy)
        .filter(BookCopy.status == "available")
        .limit(6)
        .all()
    )
    assert len(avail_copies) >= 6

    # 1. Độc giả DG004 đang có phiếu quá hạn trong seed
    overdue_reader = db_session.query(Reader).filter(Reader.card_no == "DG004").first()
    res_overdue = client.post(
        "/api/loans",
        json={"reader_id": overdue_reader.id, "copy_id": avail_copies[0].id},
    )
    assert res_overdue.status_code == 400
    assert "quá hạn" in res_overdue.json()["detail"].lower()

    # 2. Độc giả DG010 (hiện có 0 phiếu đang mượn) mượn liên tiếp 5 cuốn -> thành công, cuốn thứ 6 -> bị chặn
    clean_reader = db_session.query(Reader).filter(Reader.card_no == "DG010").first()
    for i in range(MAX_ACTIVE_LOANS):
        r = client.post(
            "/api/loans",
            json={"reader_id": clean_reader.id, "copy_id": avail_copies[i].id},
        )
        assert r.status_code == 201

    res_sixth = client.post(
        "/api/loans",
        json={"reader_id": clean_reader.id, "copy_id": avail_copies[MAX_ACTIVE_LOANS].id},
    )
    assert res_sixth.status_code == 400
    assert "tối đa 5" in res_sixth.json()["detail"].lower()


# =====================================================================
# NV2: Transaction & không thể có 2 phiếu chưa trả trên cùng 1 bản sao
# =====================================================================
def test_nv2_cannot_create_second_active_loan_on_same_copy(client, db_session):
    """NV2: Không thể tạo phiếu mượn thứ hai khi bản sao chưa trả (cả qua API lẫn ràng buộc Unique Index DB)."""
    borrowed_copy = db_session.query(BookCopy).filter(BookCopy.barcode == "BS-001-01").first()
    reader = db_session.query(Reader).filter(Reader.card_no == "DG010").first()

    # 1. Qua API trả về lỗi 400 rõ lý do
    res = client.post(
        "/api/loans",
        json={"reader_id": reader.id, "copy_id": borrowed_copy.id},
    )
    assert res.status_code in (400, 409)
    assert "chưa trả" in res.json()["detail"].lower() or "đang được mượn" in res.json()["detail"].lower()

    # 2. Thử chèn trực tiếp vào DB để chứng minh Partial Unique Index uq_loans_active_copy hoạt động
    duplicate_loan = Loan(
        reader_id=reader.id,
        copy_id=borrowed_copy.id,
        borrowed_at="2026-11-23",
        due_date="2026-12-07",
        returned_at=None,
    )
    db_session.add(duplicate_loan)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# =====================================================================
# NV3: Trả sách (normal / damaged / lost), trả lần 2 -> 409, tính phí phạt trả trễ
# =====================================================================
@pytest.mark.parametrize(
    "condition,expected_copy_status,expected_label",
    [
        ("normal", "available", "Còn trong kho"),
        ("damaged", "damaged", "Hư hỏng"),
        ("lost", "lost", "Thất lạc"),
    ],
)
def test_nv3_return_conditions_and_second_return_409(
    client, db_session, condition, expected_copy_status, expected_label
):
    """NV3: Trả sách với tình trạng normal/damaged/lost cập nhật đúng bản sao; trả lần 2 báo lỗi 409."""
    active_loan = (
        db_session.query(Loan)
        .filter(Loan.returned_at.is_(None))
        .first()
    )
    assert active_loan is not None
    copy_id = active_loan.copy_id

    res = client.post(
        f"/api/loans/{active_loan.id}/return",
        json={"return_condition": condition, "note": f"Trả tình trạng {condition}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "returned"
    assert body["return_condition"] == condition
    assert body["returned_at"] is not None

    # Kiểm tra trạng thái bản sao
    copy_obj = db_session.query(BookCopy).filter(BookCopy.id == copy_id).first()
    assert copy_obj.status == expected_copy_status

    # Trả lần 2 trên cùng phiếu -> HTTP 409
    res_second = client.post(
        f"/api/loans/{active_loan.id}/return",
        json={"return_condition": "normal"},
    )
    assert res_second.status_code == 409
    assert "đã được trả" in res_second.json()["detail"].lower()


def test_nv3_late_return_calculates_exact_fine(client, db_session):
    """NV3: Trả sách quá hạn tính đúng fine_amount = ngày trễ * FINE_PER_DAY (1000)."""
    today = get_today()
    # Tìm phiếu quá hạn 6 ngày của DG004 trong seed (due_offset = -6)
    reader_dg004 = db_session.query(Reader).filter(Reader.card_no == "DG004").first()
    overdue_loan = (
        db_session.query(Loan)
        .filter(Loan.reader_id == reader_dg004.id, Loan.returned_at.is_(None))
        .first()
    )
    assert overdue_loan is not None
    expected_late_days = (today - date.fromisoformat(overdue_loan.due_date)).days
    assert expected_late_days == 6

    res = client.post(
        f"/api/loans/{overdue_loan.id}/return",
        json={"return_condition": "normal"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fine_amount"] == 6 * FINE_PER_DAY == 6000


# =====================================================================
# NV4: Gia hạn phiếu mượn & các điều kiện từ chối
# =====================================================================
def test_nv4_renew_loan_success_and_rejections(client, db_session):
    """NV4: Gia hạn thành công cộng 7 ngày và tăng renew_count; chặn khi quá hạn, đủ 2 lần hoặc đã trả."""
    # 1. Gia hạn thành công trên phiếu đang mượn của DG001 (renew_count=0 -> 1 -> 2)
    reader_dg001 = db_session.query(Reader).filter(Reader.card_no == "DG001").first()
    loan = (
        db_session.query(Loan)
        .filter(Loan.reader_id == reader_dg001.id, Loan.returned_at.is_(None))
        .first()
    )
    orig_due = date.fromisoformat(loan.due_date)

    res1 = client.post(f"/api/loans/{loan.id}/renew")
    assert res1.status_code == 200
    b1 = res1.json()
    assert b1["renew_count"] == 1
    assert b1["due_date"] == (orig_due + timedelta(days=RENEW_DAYS)).isoformat()

    res2 = client.post(f"/api/loans/{loan.id}/renew")
    assert res2.status_code == 200
    b2 = res2.json()
    assert b2["renew_count"] == 2
    assert b2["due_date"] == (orig_due + timedelta(days=RENEW_DAYS * 2)).isoformat()

    # 2. Gia hạn lần 3 (vượt MAX_RENEWALS=2) -> bị từ chối 400
    res3 = client.post(f"/api/loans/{loan.id}/renew")
    assert res3.status_code == 400
    assert "tối đa" in res3.json()["detail"].lower()

    # 3. Gia hạn phiếu đã quá hạn (phiếu của DG004) -> bị từ chối 400
    reader_dg004 = db_session.query(Reader).filter(Reader.card_no == "DG004").first()
    overdue_loan = (
        db_session.query(Loan)
        .filter(Loan.reader_id == reader_dg004.id, Loan.returned_at.is_(None))
        .first()
    )
    res_overdue = client.post(f"/api/loans/{overdue_loan.id}/renew")
    assert res_overdue.status_code == 400
    assert "quá hạn" in res_overdue.json()["detail"].lower()

    # 4. Gia hạn phiếu đã trả -> bị từ chối 400
    returned_loan = db_session.query(Loan).filter(Loan.returned_at.is_not(None)).first()
    res_returned = client.post(f"/api/loans/{returned_loan.id}/renew")
    assert res_returned.status_code == 400
    assert "đã trả" in res_returned.json()["detail"].lower()


# =====================================================================
# NV5: Nhận diện quá hạn tự động theo hàm clock (get_today)
# =====================================================================
def test_nv5_overdue_detection_follows_clock_override(client, db_session):
    """NV5: Khi dời đồng hồ sang tương lai vượt quá due_date, phiếu đang mượn tự suy ra 'overdue'."""
    reader_dg001 = db_session.query(Reader).filter(Reader.card_no == "DG001").first()
    loan = (
        db_session.query(Loan)
        .filter(Loan.reader_id == reader_dg001.id, Loan.returned_at.is_(None))
        .first()
    )
    due = date.fromisoformat(loan.due_date)

    # Trước khi quá hạn
    res_before = client.get(f"/api/loans/{loan.id}").json()
    assert res_before["status"] == "borrowed"
    assert res_before["overdue_days"] == 0

    # Dời ngày hôm nay sang due_date + 5 ngày
    set_today_override(lambda: due + timedelta(days=5))
    res_after = client.get(f"/api/loans/{loan.id}").json()
    assert res_after["status"] == "overdue"
    assert res_after["status_label"] == "Quá hạn"
    assert res_after["overdue_days"] == 5
    assert res_after["estimated_fine"] == 5 * FINE_PER_DAY


# =====================================================================
# NV6: Không đổi tay bản sao sang hoặc ra khỏi trạng thái 'Đang mượn'
# =====================================================================
def test_nv6_manual_copy_status_change_restrictions(client, db_session):
    """NV6: Cấm đổi tay sang 'borrowed' hoặc từ 'borrowed' ra trạng thái khác; cho phép available <-> damaged."""
    avail_copy = db_session.query(BookCopy).filter(BookCopy.status == "available").first()
    borrowed_copy = db_session.query(BookCopy).filter(BookCopy.status == "borrowed").first()

    # 1. Cấm đổi tay từ available sang borrowed
    res_to_borrowed = client.patch(
        f"/api/copies/{avail_copy.id}",
        json={"status": "borrowed"},
    )
    assert res_to_borrowed.status_code == 400
    assert "đang mượn" in res_to_borrowed.json()["detail"].lower()

    # 2. Cấm đổi tay từ borrowed sang available/damaged
    res_from_borrowed = client.patch(
        f"/api/copies/{borrowed_copy.id}",
        json={"status": "available"},
    )
    assert res_from_borrowed.status_code == 400
    assert "đang được độc giả mượn" in res_from_borrowed.json()["detail"].lower()

    # 3. Cho phép đổi hợp lệ từ available sang damaged khi không có phiếu mượn
    res_valid = client.patch(
        f"/api/copies/{avail_copy.id}",
        json={"status": "damaged", "note": "Bìa sách bị ướt"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "damaged"
    assert res_valid.json()["status_label"] == "Hư hỏng"


# =====================================================================
# NV7: Chặn xoá mềm sách / vô hiệu hoá độc giả khi còn sách đang mượn; giữ lịch sử
# =====================================================================
def test_nv7_block_delete_book_and_deactivate_reader_with_active_loans(client, db_session):
    """NV7: Chặn xoá sách đang có bản sao cho mượn; chặn khoá độc giả còn sách chưa trả; bảo toàn lịch sử."""
    # 1. Đầu sách #1 ('Lập trình Python cơ bản') đang có bản sao BS-001-01 được DG001 mượn
    book1 = db_session.query(Book).filter(Book.title == "Lập trình Python cơ bản").first()
    res_del_blocked = client.delete(f"/api/books/{book1.id}")
    assert res_del_blocked.status_code == 400
    assert "chưa trả" in res_del_blocked.json()["detail"].lower()

    # 2. Độc giả DG001 đang có sách chưa trả -> chặn vô hiệu hoá
    reader1 = db_session.query(Reader).filter(Reader.card_no == "DG001").first()
    res_deact_blocked = client.patch(
        f"/api/readers/{reader1.id}/status",
        json={"is_active": False},
    )
    assert res_deact_blocked.status_code == 400
    assert "chưa trả" in res_deact_blocked.json()["detail"].lower()

    # 3. Sau khi DG001 trả phiếu đang mượn -> cho phép vô hiệu hoá và lịch sử mượn vẫn còn đủ 3 phiếu
    active_loan = (
        db_session.query(Loan)
        .filter(Loan.reader_id == reader1.id, Loan.returned_at.is_(None))
        .first()
    )
    client.post(f"/api/loans/{active_loan.id}/return", json={"return_condition": "normal"})

    res_deact_ok = client.patch(
        f"/api/readers/{reader1.id}/status",
        json={"is_active": False},
    )
    assert res_deact_ok.status_code == 200
    assert res_deact_ok.json()["is_active"] is False

    history = client.get(f"/api/readers/{reader1.id}/loans").json()
    assert history["total"] == 3


# =====================================================================
# NV8: Lịch sử mượn của độc giả, lọc theo trạng thái và phân trang
# =====================================================================
def test_nv8_reader_loan_history_filtering_and_pagination(client, db_session):
    """NV8: Xem danh sách phiếu của độc giả DG001 (1 đang mượn, 2 đã trả), hỗ trợ lọc trạng thái và phân trang."""
    reader1 = db_session.query(Reader).filter(Reader.card_no == "DG001").first()

    # Tất cả phiếu của DG001
    all_res = client.get(f"/api/readers/{reader1.id}/loans", params={"page": 1, "page_size": 2})
    assert all_res.status_code == 200
    body_all = all_res.json()
    assert body_all["total"] == 3
    assert body_all["total_pages"] == 2
    assert len(body_all["items"]) == 2
    for item in body_all["items"]:
        assert {"book_title", "copy_barcode", "borrowed_at", "due_date", "returned_at", "status"}.issubset(
            item.keys()
        )

    # Lọc chỉ phiếu đang mượn (borrowed)
    borrowed_res = client.get(f"/api/readers/{reader1.id}/loans", params={"status": "borrowed"}).json()
    assert borrowed_res["total"] == 1
    assert borrowed_res["items"][0]["status"] == "borrowed"

    # Lọc chỉ phiếu đã trả (returned)
    returned_res = client.get(f"/api/readers/{reader1.id}/loans", params={"status": "returned"}).json()
    assert returned_res["total"] == 2
    assert all(i["status"] == "returned" for i in returned_res["items"])


# =====================================================================
# NV9: Thống kê tổng quan khớp chính xác dữ liệu seed
# =====================================================================
def test_nv9_overview_statistics_match_seed_data(client):
    """NV9: Kiểm tra toàn bộ chỉ số thống kê từ GET /api/stats khớp với dữ liệu seed."""
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()

    assert stats["total_books"] == 36
    copies = stats["copies_by_status"]
    assert copies["borrowed"] == 9  # 5 đang mượn + 4 quá hạn
    assert copies["damaged"] == 1
    assert copies["lost"] == 1
    assert copies["available"] + copies["borrowed"] + copies["damaged"] + copies["lost"] == copies["total"]

    assert stats["active_loans_count"] == 9
    assert stats["overdue_loans_count"] == 4
    assert stats["returned_loans_count"] == 13
    assert stats["active_readers_count"] == 11
    assert stats["total_readers_count"] == 12

    top_books = stats["top_borrowed_books"]
    assert len(top_books) == 5
    # Sách top 1 là 'Lập trình Python cơ bản' (có 3 lượt mượn trong seed: BS-001-01, BS-001-02, BS-001-03)
    assert top_books[0]["title"] == "Lập trình Python cơ bản"
    assert top_books[0]["loan_count"] == 3
    counts = [b["loan_count"] for b in top_books]
    assert counts == sorted(counts, reverse=True)
