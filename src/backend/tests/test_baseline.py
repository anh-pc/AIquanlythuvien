def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "AIquanlythuvien"}


def test_borrow_and_return_flow(client):
    res_list = client.get("/api/borrowings")
    assert res_list.status_code == 200
    initial_records = res_list.json()
    assert len(initial_records) == 1

    # Mượn sách mới
    res_borrow = client.post(
        "/api/borrowings",
        json={"book_id": 2, "member_id": 2, "loan_days": 7, "notes": "Test mượn sách"},
    )
    assert res_borrow.status_code == 200
    borrowed = res_borrow.json()
    assert borrowed["status"] == "borrowed"
    assert borrowed["book_id"] == 2

    # Trả sách
    res_return = client.post(f"/api/borrowings/{borrowed['id']}/return")
    assert res_return.status_code == 200
    returned = res_return.json()
    assert returned["status"] in ("returned", "overdue")
    assert returned["return_date"] is not None
