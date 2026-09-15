from fastapi import FastAPI

app = FastAPI(title="C2C-DTB", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
