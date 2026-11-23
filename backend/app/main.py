from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accesos, auth

app = FastAPI(title="MVP Parqueadero")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(accesos.admin, prefix="/api/v1")
app.include_router(accesos.consultas, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
