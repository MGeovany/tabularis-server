from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import auth, convert, history, usage

app = FastAPI(
    title="Tabularis API",
    description="Backend for Tabular — PDF to Excel conversion with Supabase Auth",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(convert.router, prefix="/api/v1", tags=["convert"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(usage.router, prefix="/api/v1", tags=["usage"])


@app.get("/health")
def health():
    return {"status": "ok"}
