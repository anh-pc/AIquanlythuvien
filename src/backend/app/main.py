from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import ai_assistant, books, borrowings, categories

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AIquanlythuvien - Hệ thống Quản lý Thư viện",
    version="1.0.0",
    description="API Quản lý Sách, Thể loại, Mượn/Trả và Trợ lý AI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(categories.router)
app.include_router(borrowings.router)
app.include_router(ai_assistant.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AIquanlythuvien"}
