# NHẬT KÝ SỬ DỤNG CÔNG CỤ AI (AI WORKFLOW LOG — LAB 02)

Tài liệu này ghi lại trung thực từng giai đoạn (Phase 0 → Phase 10) trong quá trình sử dụng Antigravity IDE để kiểm toán, điều chỉnh và xây dựng hoàn chỉnh hệ thống Quản lý Thư viện **AIquanlythuvien**.

---

## Bối cảnh trước khi bắt đầu phiên LAB 02
- Ở phiên làm việc đầu tiên, repository đã được chạy một prompt có phạm vi hẹp (chỉ yêu cầu xây dựng chức năng *Tìm kiếm sách theo tên sách + Lọc theo thể loại*, với 8 thể loại, 16 đầu sách, mượn/trả sơ lược trực tiếp trên `book_id` và cấm sửa schema hay mở rộng mượn–trả).
- Khi chuyển sang yêu cầu chuẩn của **LAB 02**, hệ thống cần đáp ứng đầy đủ các chức năng **F1–F11**, quy tắc nghiệp vụ **NV1–NV9** (quản lý từng bản sao vật lý `book_copies`, độc giả `readers`, phiếu mượn `loans` có gia hạn và tính phí phạt, tra cứu theo tên sách **hoặc tác giả** tiếng Việt có dấu) và bộ hồ sơ bàn giao **D1–D5**.

---

## Phase 0 — Kiểm toán hiện trạng & Sao lưu
- **Mục tiêu:** Đánh giá toàn bộ trạng thái git, sao lưu working tree an toàn, chạy baseline test hiện có và lập bảng khoảng cách (Gap Analysis) giữa code phiên trước với đề LAB 02.
- **Việc đã làm & Lệnh chính:**
  - Chạy `git status`, `git branch --show-current`, `git log --oneline -15`, `git remote -v`.
  - Sao lưu toàn bộ mã nguồn sang thư mục ngoài repo (`scratch/_backup_truoc_lab02`).
  - Chạy baseline test: `python -m pytest -q` (`17 passed in 0.83s`) và `npm run lint && npm run build && npm test` (`3 passed`).
  - Lập bảng khoảng cách chi tiết cho F1–F11, NV1–NV9, AC1–AC14, D1–D5.
- **Kết quả:** Xác định rõ các phần tái sử dụng được (cấu trúc FastAPI + SQLAlchemy, helper escape LIKE, combobox thể loại có debounce + race guard) và các phần thiếu cần bổ sung (bảng `book_copies`, `readers`, `loans`, tìm theo tác giả, gia hạn, phí phạt, thống kê NV9, 4 màn hình quản trị).

---

## Phase 1 & Phase 2 — Thiết kế đối chiếu, Migration cộng thêm & Nâng cấp Seed
- **Mục tiêu:** Chốt schema 5 bảng mục tiêu (`categories`, `books`, `book_copies`, `readers`, `loans`), viết hàm migration cộng thêm không làm mất dữ liệu cũ, bật `PRAGMA foreign_keys = ON`, tạo Partial Unique Index `uq_loans_active_copy` và tách dữ liệu mẫu lớn ra `seed_data.py`.
- **Việc đã làm & Lệnh chính:**
  - Tạo `src/backend/app/config.py` tập trung các hằng số (`LOAN_DAYS=14`, `MAX_ACTIVE_LOANS=5`, `MAX_RENEWALS=2`, `RENEW_DAYS=7`, `FINE_PER_DAY=1000`) và hàm `get_today()`.
  - Nâng cấp `src/backend/app/utils/search.py` và `app/database.py` đăng ký hàm SQLite UDF `u_lower` / `u_casefold` dùng `unicodedata.normalize("NFC", val).casefold()`.
  - Tạo `src/backend/seed_data.py` và `src/backend/seed.py` (hỗ trợ `--reset` và tự seed khi DB trống) với **10 thể loại, 36 đầu sách tiếng Việt có dấu, 79 bản sao, 12 độc giả, 22 phiếu mượn**.
- **Lỗi gặp & Cách sửa:**
  - *Vấn đề:* SQLite mặc định không bật kiểm tra khoá ngoại và `LOWER()` của SQLite không hạ chữ cho ký tự tiếng Việt có dấu như `Đ` → `đ`, `Ă` → `ă`.
  - *Cách sửa:* Bổ sung SQLAlchemy event listener `@event.listens_for(Engine, "connect")` chạy `PRAGMA foreign_keys = ON;` và đăng ký hàm Python `unicode_casefold` làm UDF `u_lower`.

---

## Phase 3 — Triển khai Backend nghiệp vụ (F1–F11, NV1–NV9, AC1–AC7)
- **Mục tiêu:** Cài đặt toàn bộ logic nghiệp vụ ở tầng `services/` (`category_service.py`, `book_service.py`, `reader_service.py`, `loan_service.py`, `stats_service.py`) và mở các REST routers tương ứng, đồng thời cấu hình FastAPI phục vụ trực tiếp giao diện tĩnh.
- **Việc đã làm:**
  - Mở rộng `list_books()` tìm kiếm chuỗi con trên `Book.title` **HOẶC** `Book.author` (AC1).
  - Cài đặt `create_loan()` kiểm tra đủ 5 điều kiện NV1 và chạy trong 1 transaction (NV2).
  - Cài đặt `return_loan()` xử lý 3 tình trạng trả (`normal`, `damaged`, `lost`), trả về HTTP 409 khi trả lần 2 và tính phí phạt trả trễ (NV3).
  - Cài đặt `renew_loan()` cộng 7 ngày và chặn khi quá hạn / đã trả / đủ 2 lần (NV4).
  - Cài đặt `derive_loan_status()` suy ra trạng thái phiếu động theo `get_today()` (NV5).
  - Cài đặt `update_book_copy()` chặn đổi tay sang/ra `'borrowed'` (NV6), `soft_delete_book()` và `update_reader_status()` chặn xoá/vô hiệu hoá khi còn sách đang mượn (NV7).
  - Cài đặt `get_overview_stats()` tổng hợp số liệu thống kê và Top 5 sách mượn nhiều nhất (NV9).

---

## Phase 4 — Kiểm thử tự động Backend (Pytest)
- **Mục tiêu:** Cập nhật test AC1–AC7 theo quy mô seed mới (36 sách, khớp cả tác giả và chữ `Đ`/`đ`) và viết bộ integration test mới `test_business_rules_nv1_nv9.py` phủ toàn bộ NV1–NV9.
- **Lệnh chính:** `python seed.py && python seed.py --reset && python -m pytest`
- **Lỗi gặp & Cách sửa:**
  - *Vấn đề:* Trong test `test_ac7_deleted_books_excluded_everywhere`, đầu sách *"Lập trình Python cơ bản"* có bản sao `BS-001-01` đang được độc giả `DG001` mượn trong seed mới, nên gọi `DELETE /api/books/1` ngay bị quy tắc NV7 chặn với HTTP 400.
  - *Cách sửa:* Trong test AC7, thực hiện gọi API trả phiếu đang mượn của đầu sách đó trước rồi mới gọi `DELETE /api/books/1`, đồng thời kiểm thử riêng việc chặn xoá khi đang có bản sao cho mượn tại `test_nv7_block_delete_book_and_deactivate_reader_with_active_loans`.
- **Kết quả:** Toàn bộ **35/35 test pass** (`35 passed in 4.94s`).

---

## Phase 5 & Phase 6 — Triển khai Frontend 4 màn hình & Kiểm tra UI
- **Mục tiêu:** Xây dựng 4 màn hình (`OverviewView.js`, `BooksAdminView.js`, `ReadersAdminView.js`, `LoansAdminView.js`) đáp ứng AC8–AC14 và UX1–UX7.
- **Việc đã làm & Lệnh chính:**
  - Tái sử dụng `createSearchableCategoryDropdown` ở cả thanh lọc danh sách sách và trong Form Thêm/Sửa đầu sách (AC10).
  - Bổ sung ô gõ tìm độc giả và ô gõ tìm bản sao *Còn trong kho* khi lập phiếu mượn mới (UX2).
  - Định dạng toàn bộ ngày hiển thị sang `dd/mm/yyyy` (`formatDateVN`), hiển thị rõ số ngày trễ và phí phạt trên các phiếu quá hạn (UX5).
  - Chạy `npm run lint && npm run build && npm test` → **12 modules passed lint, build thành công, 4/4 frontend unit tests pass**.
- **Ghi nhận môi trường ở Phase 6:** Công cụ Browser Subagent không thể kết nối vào Chrome của máy do thiếu file `DevToolsActivePort`. Đã ghi nhận trung thực và chuẩn bị đầy đủ 8 placeholder ảnh ứng dụng cùng kịch bản kiểm thử thủ công 10 bước.

---

## Phase 7, 8, 9 & 10 — Rà soát, Tài liệu, Kiểm chứng bản sạch, Đóng gói Zip & Push GitHub
- **Mục tiêu:** Hoàn thiện `BaoCao_Lab.md`, `README.md`, `docs/nhat_ky_AI.md`; kiểm chứng quy trình cài đặt/chạy/test từ một thư mục sạch hoàn toàn; tạo gói nộp `dist/MSSV_HoTen_LabQLThuVien.zip`; quét secret và push lên GitHub.
- **Kết quả:** Toàn bộ tài liệu khớp 100% với mã nguồn thực tế, kiểm chứng bản sạch thành công, không có bất kỳ secret hay file rác nào trong git và file zip.
