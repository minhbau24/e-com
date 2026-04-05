"""FastAPI entrypoint for e-com service (behavior excluded)."""

import logging

from fastapi import FastAPI

from api.chat import router as chat_router
from api.recommend import router as recommend_router
from api.search import router as search_router
from api.track import router as track_router
from core.logging import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI(
	title="E-com AI Service",
	version="0.1.0",
	description="RAG + DB + LangGraph chatbot backend (without behavior module).",
)


@app.on_event("startup")
def configure_runtime_logging() -> None:
	# Uvicorn may override logging config during boot; re-apply once startup runs.
	setup_logging()
	logger.info("Runtime logging configured on startup")


@app.get("/health")
def health() -> dict:
	return {"status": "ok"}


app.include_router(chat_router)
app.include_router(search_router)
app.include_router(recommend_router)
app.include_router(track_router)
