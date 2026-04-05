"""Chat API routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.rag_service import run_chat


router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
	user_id: str = Field(default="anonymous", min_length=1)
	query: str = Field(..., min_length=1)
	debug: bool = False


class ChatResponse(BaseModel):
	user_id: str
	query: str
	response: str
	intent: Optional[str] = None
	debug: Optional[Dict[str, Any]] = None


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
	logger.info("[api.chat] request | user_id=%s | debug=%s | query=%s", request.user_id, request.debug, request.query[:160])
	try:
		result = run_chat(query=request.query, user_id=request.user_id, debug=request.debug)
		if result.get("error"):
			logger.error("[api.chat] graph error | user_id=%s | error=%s", request.user_id, result.get("error"))
			raise HTTPException(status_code=500, detail=str(result["error"]))
		logger.info("[api.chat] response | user_id=%s | intent=%s", request.user_id, result.get("intent"))
		return ChatResponse(**result)
	except HTTPException:
		raise
	except Exception as exc:
		logger.exception("[api.chat] unexpected error | user_id=%s | error=%s", request.user_id, exc)
		raise HTTPException(status_code=500, detail=str(exc)) from exc
