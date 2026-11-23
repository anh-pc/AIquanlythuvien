# AIquanlythuvien — Hệ thống Quản lý Thư viện Số (LAB 02)

Hệ thống quản lý thư viện thay thế sổ sách thủ công, cho phép quản lý tách biệt **Đầu sách** và từng **Bản sao vật lý** (`Còn trong kho`, `Đang mượn`, `Hư hỏng`, `Thất lạc`), quản lý **Độc giả**, thực hiện nghiệp vụ **Mượn – Trả – Gia hạn – Tính phí phạt quá hạn** (NV1–NV9), tra cứu nhanh theo **tên sách hoặc tác giả** tiếng Việt có dấu (AC1–AC14) và xem thống kê tổng quan. Ứng dụng chạy hoàn toàn offline, không yêu cầu bất kỳ API key nào.

## 1. Yêu cầu môi trường

- **Python:** `>= 3.11` (đã kiểm chứng trên Python `3.13.14`)
- **Node.js & npm (tuỳ chọn, dùng cho script lint/test frontend):** `Node.js >= 20` (đã kiểm chứng trên Node.js `v22.23.4`)
- **Cơ sở dữ liệu:** SQLite 3 (tích hợp sẵn trong Python)

## 2. Cài đặt

### Trên Windows (PowerShell):
```powershell
python -m pip install -r src/backend/requirements.txt
Copy-Item .env.example .env
```

### Trên macOS / Linux (Bash/Zsh):
```bash
python3 -m pip install -r src/backend/requirements.txt
cp .env.example .env
```

## 3. Cấu hình môi trường (Tuỳ chọn)

File `.env.example` đã chứa sẵn các giá trị mặc định an toàn. Hệ thống **không yêu cầu bất kỳ API key nào** để chạy toàn bộ chức năng quản lý thư viện:
- `DATABASE_URL`: Đường dẫn file SQLite (mặc định tự tạo `src/backend/library.db`).
- `BACKEND_PORT`: Cổng chạy server FastAPI (mặc định `8000`).

## 4. Khởi chạy ứng dụng

Khi khởi động, nếu cơ sở dữ liệu còn trống, hệ thống sẽ **tự động khởi tạo bảng và nạp dữ liệu mẫu** (10 thể loại, 36 đầu sách tiếng Việt có dấu, 79 bản sao, 12 độc giả, 22 phiếu mượn). FastAPI phục vụ trực tiếp cả REST API lẫn giao diện Web tại cùng địa chỉ:

### Trên Windows (PowerShell):
```powershell
cd src/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Trên macOS / Linux:
```bash
cd src/backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **Giao diện Quản lý Thư viện (4 màn hình):** http://127.0.0.1:8000
- **Tài liệu REST API (Swagger UI):** http://127.0.0.1:8000/docs

*(Tuỳ chọn: Nếu muốn chạy thêm dev server riêng cho Frontend tại `http://127.0.0.1:5173`, mở terminal khác tại `src/frontend` và chạy `npm run dev`).*

## 5. Nạp lại dữ liệu mẫu (`--reset`)

Để đặt lại toàn bộ cơ sở dữ liệu của ứng dụng về trạng thái dữ liệu mẫu chuẩn ban đầu:

```powershell
# Windows PowerShell
cd src/backend
python seed.py --reset
cd ../..
```

```bash
# macOS / Linux
cd src/backend
python3 seed.py --reset
cd ../..
```

## 6. Chạy kiểm thử tự động (Automated Tests)

Bộ kiểm thử tạo cơ sở dữ liệu SQLite in-memory tạm thời riêng biệt, **không làm ảnh hưởng** đến file dữ liệu đang chạy của ứng dụng:

```powershell
# 1. Chạy 35 integration tests phía Backend (AC1–AC7 & NV1–NV9)
cd src/backend
python -m pytest
cd ../..

# 2. Chạy lint, build và 4 unit tests phía Frontend
cd src/frontend
npm run lint
npm run build
npm test
cd ../..
```

## 7. Dữ liệu mẫu tiêu biểu (được tạo bởi `src/backend/seed.py`)

- **Độc giả mẫu (`readers`):**
  - `DG001` — Nguyễn Minh Tuấn (Đang hoạt động, đang mượn 1 cuốn, đã trả 2 cuốn)
  - `DG004` — Lê Hoàng Bách (Đang hoạt động, có 1 phiếu quá hạn 6 ngày)
  - `DG010` — Ngô Gia Bảo (Đang hoạt động, không có phiếu đang mượn — dùng để test mượn mới)
  - `DG012` — Trịnh Quốc Khánh (Đã bị vô hiệu hoá `is_active=False`)
- **Đầu sách & Bản sao mẫu (`books`, `book_copies`):**
  - *"Lập trình Python cơ bản"* — Nguyễn Văn Minh (`BS-001-01` đang mượn; `BS-001-02`..`04` còn trong kho)
  - *"Thiết kế Cơ sở dữ liệu Quan hệ"* — Đặng Thanh Tùng (`BS-005-01`, `BS-005-02`)
  - *"Đất Rừng Phương Nam"* — Đoàn Giỏi (`BS-022-01`, `BS-022-02`)

## 8. Cấu trúc thư mục

```text
Lab_QLThuVien_[MSSV]_[HoTen]/
├── BaoCao_Lab.md               # (D1) Báo cáo phân tích, thiết kế, sơ đồ Mermaid & kết quả kiểm thử
├── README.md                   # (D3) Hướng dẫn cài đặt, khởi chạy, seed dữ liệu và chạy test
├── .env.example                # Mẫu cấu hình biến môi trường (không chứa secret)
├── .gitignore                  # Quy tắc loại trừ venv, node_modules, .env, *.db, dist/, *.zip
├── docs/
│   ├── nhat_ky_AI.md           # (D4) Nhật ký thực tế quá trình làm việc qua các Phase với AI
│   └── screenshots/            # Thư mục lưu ảnh chụp ứng dụng và ảnh quá trình dùng AI
└── src/                        # (D2) Toàn bộ mã nguồn ứng dụng, dữ liệu mẫu và kiểm thử
    ├── backend/
    │   ├── app/                # config.py, database.py, models.py, schemas.py, services/, routers/, utils/
    │   ├── tests/              # 35 Pytest integration tests (AC1–AC7, NV1–NV9)
    │   ├── seed_data.py        # Dữ liệu mẫu tách riêng (10 thể loại, 36 sách, 12 độc giả, 22 phiếu)
    │   ├── seed.py             # Script nạp dữ liệu mẫu (hỗ trợ cờ --reset)
    │   └── requirements.txt    # Danh sách thư viện Python
    └── frontend/
        ├── index.html          # Giao diện chính
        ├── src/                # 4 màn hình (Overview, Books, Readers, Loans), Components, Utils, CSS
        ├── scripts/            # Scripts hỗ trợ lint, build, dev server
        └── tests/              # Unit tests cho query builder, debounce, race guard, định dạng ngày
```

👉 Xem báo cáo phân tích thiết kế chi tiết tại [BaoCao_Lab.md](file:///d:/Lab_QLThuVien_29211555982_DANGVANANH/BaoCao_Lab.md) và nhật ký làm việc với AI tại [docs/nhat_ky_AI.md](file:///d:/Lab_QLThuVien_29211555982_DANGVANANH/docs/nhat_ky_AI.md).
