from fastapi import FastAPI

app = FastAPI(title="MVP Parqueadero")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
