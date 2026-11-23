import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.database import ensure_schema_and_migrations, engine
from app.routers import (
    ai_assistant,
    books,
    borrowings,
    categories,
    copies,
    loans,
    readers,
    stats,
)
from seed import ensure_seeded_if_empty


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    ensure_seeded_if_empty()
    yield


ensure_schema_and_migrations(engine)

app = FastAPI(
    title="AIquanlythuvien - Hệ thống Quản lý Thư viện",
    version="2.0.0",
    description="API Quản lý Đầu sách, Bản sao, Độc giả, Mượn/Trả/Gia hạn, Thống kê và Trợ lý AI",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(books.router)
app.include_router(copies.router)
app.include_router(readers.router)
app.include_router(loans.router)
app.include_router(stats.router)
app.include_router(borrowings.router)
app.include_router(ai_assistant.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AIquanlythuvien"}


# Phục vụ trực tiếp giao diện Frontend (HTML/CSS/JS thuần) từ FastAPI để chạy offline không cần build step
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)
FRONTEND_SRC_DIR = os.path.join(FRONTEND_DIR, "src")

if os.path.isdir(FRONTEND_SRC_DIR):
    app.mount("/src", StaticFiles(directory=FRONTEND_SRC_DIR), name="frontend_src")


@app.get("/", include_in_schema=False)
def serve_frontend_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "AIquanlythuvien API is running. Visit /docs for Swagger UI."}
