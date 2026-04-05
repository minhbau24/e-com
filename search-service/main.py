"""FastAPI entrypoint for the search service."""

from fastapi import FastAPI

from api.search import router as search_router
from core.logging import configure_logging


configure_logging()


app = FastAPI(
    title="E-com Search Service",
    version="0.1.0",
    description="Dedicated product search API for LLM and downstream services.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(search_router)
