import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.db import init_db
from app.routes import stats, users, repos, graph, analytics, analysis, export, real_scan

app = FastAPI(
    title=settings.API_TITLE,
    description="GitHub star-fraud detection backed by a real trained GraphSAGE GNN.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(repos.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(real_scan.router, prefix="/api")


@app.on_event("startup")
async def startup():
    init_db()
    if not os.path.exists(settings.DATABASE_PATH) or os.path.getsize(settings.DATABASE_PATH) < 4096:
        print("No trained data found — run `python -m app.services.pipeline` once before starting the API.")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
