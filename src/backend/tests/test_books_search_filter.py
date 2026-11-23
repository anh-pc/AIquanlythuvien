import pytest
from app.models import Book, BookCopy, Category, Loan


def _assert_book_list_format(body: dict):
    """Kiểm tra cấu trúc response chuẩn {items, total, page, page_size, total_pages}."""
    assert set(body.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert isinstance(body["page"], int)
    assert isinstance(body["page_size"], int)
    assert isinstance(body["total_pages"], int)
    for item in body["items"]:
        assert {
            "id",
            "title",
            "author",
            "isbn",
            "publisher",
            "published_year",
            "category_id",
            "category_name",
            "total_copies",
            "available_copies",
            "is_deleted",
        }.issubset(item.keys())


# =====================================================================
# AC1: Tìm theo tên sách HOẶC tác giả (substring, case-insensitive, chữ Đ/đ, trim, rỗng/whitespace)
# =====================================================================
@pytest.mark.parametrize(
    "query_kw",
    [
        "python",
        "PYTHON",
        "trình Pyt",
        "  python  ",
        "LẬP TRÌNH PYTHON",
    ],
)
def test_ac1_search_by_title_normalized_matches_seed_book(client, query_kw):
    """AC1: Các biến thể hoa/thường, substring và khoảng trắng đều tìm thấy 'Lập trình Python cơ bản'."""
    res = client.get("/api/books", params={"q": query_kw, "page_size": 50})
    assert res.status_code == 200
    body = res.json()
    _assert_book_list_format(body)

    titles = [b["title"] for b in body["items"]]
    assert "Lập trình Python cơ bản" in titles
    for item in body["items"]:
        kw_folded = query_kw.strip().casefold()
        assert kw_folded in item["title"].casefold() or kw_folded in item["author"].casefold()


@pytest.mark.parametrize(
    "author_kw,expected_author,expected_title",
    [
        ("đặng thanh tùng", "Đặng Thanh Tùng", "Thiết kế Cơ sở dữ liệu Quan hệ"),
        ("ĐẶNG THANH TÙNG", "Đặng Thanh Tùng", "Thiết kế Cơ sở dữ liệu Quan hệ"),
        ("  Đoàn Giỏi  ", "Đoàn Giỏi", "Đất Rừng Phương Nam"),
        ("đoàn giỏi", "Đoàn Giỏi", "Đất Rừng Phương Nam"),
    ],
)
def test_ac1_search_by_author_and_vietnamese_d_case_insensitive(
    client, author_kw, expected_author, expected_title
):
    """AC1: Tìm theo tên tác giả và kiểm chứng chữ có dấu tiếng Việt (Đ/đ) không phân biệt hoa/thường."""
    res = client.get("/api/books", params={"q": author_kw, "page_size": 50})
    assert res.status_code == 200
    body = res.json()
    _assert_book_list_format(body)
    assert body["total"] >= 1
    titles = [b["title"] for b in body["items"]]
    authors = [b["author"] for b in body["items"]]
    assert expected_title in titles
    assert expected_author in authors


@pytest.mark.parametrize("empty_kw", ["", "   ", "\t  \n"])
def test_ac1_empty_or_whitespace_keyword_does_not_filter(client, empty_kw):
    """AC1: Keyword rỗng hoặc chỉ chứa khoảng trắng thì bỏ filter, trả về toàn bộ 36 đầu sách."""
    baseline = client.get("/api/books", params={"page_size": 100}).json()
    res = client.get("/api/books", params={"q": empty_kw, "page_size": 100})
    assert res.status_code == 200
    body = res.json()
    _assert_book_list_format(body)
    assert body["total"] == baseline["total"] == 36
    assert len(body["items"]) == 36


# =====================================================================
# AC2: Truyền ID thể loại -> chỉ trả sách thuộc thể loại đó
# =====================================================================
def test_ac2_filter_by_category_id(client, db_session):
    """AC2: Lọc theo ID thể loại 'Công nghệ thông tin' chỉ trả về đúng 12 sách thuộc thể loại đó."""
    it_category = db_session.query(Category).filter(Category.name == "Công nghệ thông tin").first()
    assert it_category is not None

    res = client.get("/api/books", params={"category_id": it_category.id, "page_size": 50})
    assert res.status_code == 200
    body = res.json()
    _assert_book_list_format(body)

    assert body["total"] == 12
    assert len(body["items"]) == 12
    for item in body["items"]:
        assert item["category_id"] == it_category.id
        assert item["category_name"] == "Công nghệ thông tin"


# =====================================================================
# AC3: Keyword + thể loại cùng lúc -> AND (không OR)
# =====================================================================
def test_ac3_combine_keyword_and_category_uses_and_logic(client, db_session):
    """
    AC3: Trong seed có 3 sách chứa 'Python':
    - 2 sách thuộc 'Công nghệ thông tin' ('Lập trình Python cơ bản', 'Lập trình Python nâng cao cho Web')
    - 1 sách thuộc 'Khoa học dữ liệu & AI' ('Phân tích dữ liệu với Python và Pandas')
    Và thể loại 'Công nghệ thông tin' có tổng cộng 12 sách.
    Khi lọc q='Python' VÀ category_id='Công nghệ thông tin':
    - Logic AND trả về đúng 2 sách.
    - Logic OR sẽ trả về 12 + 1 = 13 sách.
    """
    it_category = db_session.query(Category).filter(Category.name == "Công nghệ thông tin").first()
    res = client.get(
        "/api/books",
        params={"q": "Python", "category_id": it_category.id, "page_size": 20},
    )
    assert res.status_code == 200
    body = res.json()
    _assert_book_list_format(body)

    assert body["total"] == 2
    titles = [b["title"] for b in body["items"]]
    assert titles == [
        "Lập trình Python cơ bản",
        "Lập trình Python nâng cao cho Web",
    ]


# =====================================================================
# AC4: total và số trang tính SAU khi áp mọi filter; phân trang trên tập đã lọc
# =====================================================================
def test_ac4_total_and_pagination_calculated_after_filters(client, db_session):
    """
    AC4: Thể loại 'Công nghệ thông tin' có 12 sách trong seed.
    Khi lọc category_id với page_size=10 (mặc định):
    - total = 12, total_pages = 2
    - Trang 1 có 10 sách, Trang 2 có 2 sách, không trùng lặp ID.
    """
    it_category = db_session.query(Category).filter(Category.name == "Công nghệ thông tin").first()

    page1_res = client.get(
        "/api/books",
        params={"category_id": it_category.id, "page": 1, "page_size": 10},
    )
    assert page1_res.status_code == 200
    p1 = page1_res.json()
    _assert_book_list_format(p1)
    assert p1["total"] == 12
    assert p1["page"] == 1
    assert p1["page_size"] == 10
    assert p1["total_pages"] == 2
    assert len(p1["items"]) == 10

    page2_res = client.get(
        "/api/books",
        params={"category_id": it_category.id, "page": 2, "page_size": 10},
    )
    assert page2_res.status_code == 200
    p2 = page2_res.json()
    _assert_book_list_format(p2)
    assert p2["total"] == 12
    assert p2["page"] == 2
    assert p2["page_size"] == 10
    assert p2["total_pages"] == 2
    assert len(p2["items"]) == 2

    p1_ids = {b["id"] for b in p1["items"]}
    p2_ids = {b["id"] for b in p2["items"]}
    assert p1_ids.isdisjoint(p2_ids)


# =====================================================================
# AC5: Keyword không khớp hoặc ID thể loại không tồn tại -> HTTP 200 + danh sách rỗng
# =====================================================================
def test_ac5_non_matching_keyword_or_non_existent_category_returns_200_empty(client):
    """AC5: Không khớp keyword hoặc category_id không tồn tại -> 200 OK + items=[], total=0."""
    res_kw = client.get("/api/books", params={"q": "SachKhongHeTonTai9999"})
    assert res_kw.status_code == 200
    body_kw = res_kw.json()
    _assert_book_list_format(body_kw)
    assert body_kw["items"] == []
    assert body_kw["total"] == 0
    assert body_kw["total_pages"] == 0

    res_cat = client.get("/api/books", params={"category_id": 999999})
    assert res_cat.status_code == 200
    body_cat = res_cat.json()
    _assert_book_list_format(body_cat)
    assert body_cat["items"] == []
    assert body_cat["total"] == 0
    assert body_cat["total_pages"] == 0

    res_invalid = client.get("/api/books", params={"category_id": "not-an-int"})
    assert res_invalid.status_code == 422


# =====================================================================
# AC6: '%', '_', '100%' được tìm đúng nghĩa literal (không phải wildcard)
# =====================================================================
def test_ac6_special_like_wildcards_are_escaped_as_literals(client, db_session):
    """
    AC6: Tạo fixture riêng cho các sách chứa ký tự '%', '_', '100%'.
    Chứng minh tìm '%', '_', '100%' chỉ khớp đúng sách chứa ký tự literal đó, không trả về toàn bộ sách.
    """
    it_category = db_session.query(Category).filter(Category.name == "Công nghệ thông tin").first()
    b_percent = Book(
        title="Bí quyết tối ưu 100% hiệu năng hệ thống",
        author="Tác giả A",
        isbn="978-604-999-101",
        publisher="NXB Test",
        published_year=2025,
        category_id=it_category.id,
        total_copies=1,
        available_copies=1,
        is_deleted=False,
    )
    b_underscore = Book(
        title="Thực hành FastAPI_SQLAlchemy chuyên sâu",
        author="Tác giả B",
        isbn="978-604-999-102",
        publisher="NXB Test",
        published_year=2025,
        category_id=it_category.id,
        total_copies=1,
        available_copies=1,
        is_deleted=False,
    )
    db_session.add_all([b_percent, b_underscore])
    db_session.commit()

    # 1. Tìm '%' -> chỉ trả về 1 sách chứa '%', không trả về toàn bộ 38 sách
    res_pct = client.get("/api/books", params={"q": "%", "page_size": 50})
    assert res_pct.status_code == 200
    body_pct = res_pct.json()
    _assert_book_list_format(body_pct)
    assert body_pct["total"] == 1
    assert body_pct["items"][0]["title"] == "Bí quyết tối ưu 100% hiệu năng hệ thống"

    # 2. Tìm '100%' -> chỉ trả về đúng sách có '100%'
    res_100 = client.get("/api/books", params={"q": "100%", "page_size": 50})
    assert res_100.status_code == 200
    body_100 = res_100.json()
    assert body_100["total"] == 1
    assert body_100["items"][0]["title"] == "Bí quyết tối ưu 100% hiệu năng hệ thống"

    # 3. Tìm '_' -> chỉ trả về đúng 1 sách chứa '_', không khớp mọi ký tự đơn
    res_und = client.get("/api/books", params={"q": "_", "page_size": 50})
    assert res_und.status_code == 200
    body_und = res_und.json()
    _assert_book_list_format(body_und)
    assert body_und["total"] == 1
    assert body_und["items"][0]["title"] == "Thực hành FastAPI_SQLAlchemy chuyên sâu"


# =====================================================================
# AC7: Sách đã xoá luôn bị loại khỏi danh sách, tìm kiếm, lọc, kết hợp, phân trang, total
# =====================================================================
def test_ac7_deleted_books_excluded_everywhere(client, db_session):
    """
    AC7: Trả phiếu đang mượn của 'Lập trình Python cơ bản' (để thoả NV7 không còn bản sao đang mượn),
    xoá mềm sách qua DELETE /api/books/{id}, sau đó kiểm tra sách đã xoá biến mất ở mọi truy vấn.
    """
    target_book = (
        db_session.query(Book)
        .filter(Book.title == "Lập trình Python cơ bản")
        .first()
    )
    assert target_book is not None
    book_id = target_book.id
    cat_id = target_book.category_id

    # Trả phiếu đang mượn trên bản sao của đầu sách này trước khi xoá mềm (tuân thủ NV7)
    copy_ids = [c.id for c in db_session.query(BookCopy).filter(BookCopy.book_id == book_id).all()]
    active_loans = (
        db_session.query(Loan)
        .filter(Loan.copy_id.in_(copy_ids), Loan.returned_at.is_(None))
        .all()
    )
    for ln in active_loans:
        client.post(f"/api/loans/{ln.id}/return", json={"return_condition": "normal"})

    # Thực hiện xoá mềm qua API
    del_res = client.delete(f"/api/books/{book_id}")
    assert del_res.status_code == 200

    # 1. Danh sách mặc định (total giảm từ 36 xuống 35)
    all_res = client.get("/api/books", params={"page_size": 50}).json()
    assert all_res["total"] == 35
    assert all(b["id"] != book_id for b in all_res["items"])

    # 2. Tìm kiếm theo keyword 'Lập trình Python cơ bản' -> rỗng
    kw_exact = client.get("/api/books", params={"q": "Lập trình Python cơ bản"}).json()
    assert kw_exact["total"] == 0
    assert kw_exact["items"] == []

    # 3. Tìm kiếm theo keyword 'Python' -> giảm từ 3 xuống 2
    kw_py = client.get("/api/books", params={"q": "Python", "page_size": 20}).json()
    assert kw_py["total"] == 2
    assert all(b["id"] != book_id for b in kw_py["items"])

    # 4. Lọc theo thể loại Công nghệ thông tin -> giảm từ 12 xuống 11
    cat_res = client.get("/api/books", params={"category_id": cat_id, "page_size": 20}).json()
    assert cat_res["total"] == 11
    assert all(b["id"] != book_id for b in cat_res["items"])

    # 5. Kết hợp keyword 'Python' + thể loại Công nghệ thông tin -> giảm từ 2 xuống 1
    combo_res = client.get(
        "/api/books",
        params={"q": "Python", "category_id": cat_id, "page_size": 20},
    ).json()
    assert combo_res["total"] == 1
    assert combo_res["items"][0]["title"] == "Lập trình Python nâng cao cho Web"


# =====================================================================
# Kiểm thử API tìm kiếm thể loại phía Backend (phục vụ AC10)
# =====================================================================
def test_categories_search_normalization_and_limit(client):
    """Kiểm tra GET /api/categories hỗ trợ q/keyword chuẩn hoá và limit."""
    res = client.get("/api/categories", params={"q": "  công nghệ  ", "limit": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Công nghệ thông tin"

    res_empty = client.get("/api/categories", params={"q": "KhongCoTheLoaiNay"})
    assert res_empty.status_code == 200
    assert res_empty.json()["items"] == []
