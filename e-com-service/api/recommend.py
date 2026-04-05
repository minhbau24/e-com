"""Recommendation API routes (non-behavior baseline)."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.db_service import search_products


router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendResponse(BaseModel):
	user_id: str
	query: str
	items: List[Dict[str, Any]]


@router.get("/{user_id}", response_model=RecommendResponse)
def recommend(user_id: str, query: str = Query(default="sách kiến trúc", min_length=1)) -> RecommendResponse:
	items = search_products(query=query, limit=10)
	return RecommendResponse(user_id=user_id, query=query, items=items)
