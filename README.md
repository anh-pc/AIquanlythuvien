# AIquanlythuvien — Hệ thống Quản lý Thư viện Số

Hệ thống quản lý thư viện hỗ trợ thủ thư tra cứu sách theo tên, lọc theo thể loại từ backend, quản lý mượn/trả sách và gợi ý sách thông minh với trợ lý AI. Toàn bộ mã nguồn, dữ liệu mẫu và bộ kiểm thử tự động được đóng gói trong thư mục `src/`.

## 1. Yêu cầu môi trường

- **Python:** `>= 3.11` (đã kiểm chứng trên Python `3.13.14`)
- **Node.js & npm:** `Node.js >= 20` (đã kiểm chứng trên Node.js `v22.23.4`, npm `10.9.9`)
- **Cơ sở dữ liệu:** SQLite 3 (tích hợp sẵn trong Python, không cần cài đặt máy chủ DB rời)

## 2. Cài đặt

Từ thư mục gốc của repository:

```powershell
# 1. Cài đặt thư viện Backend
python -m pip install -r src/backend/requirements.txt

# 2. Kiểm tra môi trường Frontend (không yêu cầu cài thêm dependency ngoài)
cd src/frontend
npm install
cd ../..
```

## 3. Cấu hình môi trường

Sao chép file `.env.example` thành `.env` ở thư mục gốc:

```powershell
Copy-Item .env.example .env
```

Các biến môi trường chính trong `.env`:
- `DATABASE_URL`: Đường dẫn kết nối SQLite (mặc định `sqlite:///./library.db`).
- `BACKEND_PORT`: Cổng chạy API FastAPI (mặc định `8000`).
- `FRONTEND_PORT`: Cổng chạy giao diện quản trị (mặc định `5173`).
- `GEMINI_API_KEY`: Khoá API Google Gemini (nếu để giá trị giả mặc định, hệ thống tự động dùng chế độ gợi ý từ kho sách cục bộ).

## 4. Nạp dữ liệu mẫu (Seed)

Chạy script nạp dữ liệu mẫu gồm **8 thể loại**, **16 đầu sách** (bao gồm *"Lập trình Python cơ bản"*), **3 tài khoản** và **1 phiếu mượn mẫu**:

```powershell
cd src/backend
python seed.py
cd ../..
```

## 5. Khởi chạy ứng dụng

Mở 2 cửa sổ terminal từ thư mục gốc:

**Terminal 1 — Khởi chạy Backend API (`http://127.0.0.1:8000`):**
```powershell
cd src/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- Tài liệu Swagger UI: `http://127.0.0.1:8000/docs`

**Terminal 2 — Khởi chạy Frontend Admin (`http://127.0.0.1:5173`):**
```powershell
cd src/frontend
npm run dev
```
- Truy cập giao diện quản trị tại: `http://127.0.0.1:5173`

## 6. Chạy kiểm thử & Build

```powershell
# Chạy toàn bộ automated tests phía Backend (Pytest - AC1 đến AC7)
cd src/backend
python -m pytest
cd ../..

# Chạy lint, build và unit tests phía Frontend
cd src/frontend
npm run lint
npm run build
npm test
cd ../..
```

## 7. Tài khoản Demo (được tạo bởi `src/backend/seed.py`)

| Mã thẻ (`member_code`) | Họ và tên | Email | Vai trò (`role`) |
|---|---|---|---|
| `LIB001` | Đặng Văn Anh (Thủ thư) | `librarian@thuvien.edu.vn` | `librarian` |
| `MEM001` | Nguyễn Minh Tuấn | `tuan.nm@student.edu.vn` | `member` |
| `MEM002` | Trần Thu Hà | `ha.tt@student.edu.vn` | `member` |

## 8. Cấu trúc thư mục

```text
.
├── BaoCao_Lab.md               # (D1) Báo cáo phân tích, thiết kế, sơ đồ Mermaid & kết quả test
├── README.md                   # (D3) Hướng dẫn cài đặt, nạp dữ liệu mẫu, chạy và kiểm thử
├── .env.example                # Mẫu cấu hình biến môi trường (giá trị giả an toàn)
├── .gitignore                  # Quy tắc loại trừ file tạm, DB cục bộ, .env, build output
├── docs/
│   └── screenshots/            # Ảnh chụp giao diện ứng dụng thực tế
└── src/                        # (D2) Toàn bộ mã nguồn ứng dụng
    ├── backend/                # FastAPI + SQLAlchemy + SQLite
    │   ├── app/                # Models, Schemas, Services, Routers, Keyword Normalizer
    │   ├── tests/              # Pytest integration tests (AC1–AC7)
    │   ├── seed.py             # Script khởi tạo dữ liệu mẫu
    │   └── requirements.txt    # Danh sách thư viện Python
    └── frontend/               # Giao diện Quản trị SPA
        ├── src/                # Views, Components, Shared API Client, Shared Types, Utils
        ├── scripts/            # Build, Lint và Dev Server scripts
        └── tests/              # Automated tests cho filter, debounce và race condition
```

👉 Xem chi tiết phân tích hệ thống, sơ đồ quy trình Mượn/Trả và cấu trúc CSDL tại [BaoCao_Lab.md](file:///d:/Lab_QLThuVien_29211555982_DANGVANANH/BaoCao_Lab.md).
