"""Search API routes."""

import logging

from fastapi import APIRouter, HTTPException

from models.search import SearchRequest, SearchResponse
from services.search_service import SearchService, SearchServiceError


router = APIRouter(prefix="/search", tags=["search"])
service = SearchService()
logger = logging.getLogger(__name__)


@router.post("", response_model=SearchResponse)
def search_products(payload: SearchRequest) -> SearchResponse:
    try:
        logger.info(
            "[api.search] received | query=%s | filters=%s | sort=%s | page=%s | size=%s",
            payload.query,
            payload.filters.model_dump(),
            payload.sort.model_dump(),
            payload.pagination.page,
            payload.pagination.size,
        )
        return service.search(payload)
    except SearchServiceError as exc:
        logger.exception("[api.search] search failed | error=%s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
