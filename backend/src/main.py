from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database import init_db, close_db
from src.database.seed import seed_admin
from src.routers import auth, questions, recognition, recommendations, export

app = FastAPI(title="错题宝 API", version="1.0.0")

# Include routers
app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(recognition.router)
app.include_router(recommendations.router)
app.include_router(export.router)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    await init_db()
    await seed_admin()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on application shutdown."""
    await close_db()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
