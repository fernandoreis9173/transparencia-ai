
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.analytics import router as analytics_router

app = FastAPI(
    title="Transparência AI API",
    description="API de análise de despesas públicas.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(analytics_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
