"""Minimal FastAPI app for EC2 smoke tests."""

from fastapi import FastAPI

app = FastAPI(title="AWS Docs Assistant (hello-world test)")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello World from FastAPI"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "message": "Hello World from FastAPI"}
