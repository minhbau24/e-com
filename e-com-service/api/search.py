"""Search proxy API routes to forward rich search payloads to search-service."""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib import error, request as urlrequest

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config import settings


router = APIRouter(prefix="/search", tags=["search"])


class SearchProxyRequest(BaseModel):
	query: str = ""
	filters: Dict[str, Any] = Field(default_factory=dict)
	sort: Dict[str, Any] = Field(default_factory=lambda: {"field": "relevance", "order": "desc"})
	pagination: Dict[str, Any] = Field(default_factory=lambda: {"page": 1, "size": 10})


@router.post("", response_model=Dict[str, Any])
def search_proxy(payload: SearchProxyRequest) -> Dict[str, Any]:
	if not settings.SEARCH_SERVICE_URL:
		raise HTTPException(status_code=500, detail="SEARCH_SERVICE_URL is not configured")

	body = json.dumps(payload.model_dump()).encode("utf-8")
	request_obj = urlrequest.Request(
		settings.SEARCH_SERVICE_URL,
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)

	try:
		with urlrequest.urlopen(request_obj, timeout=settings.SEARCH_SERVICE_TIMEOUT_SECONDS) as response:
			response_text = response.read().decode("utf-8")
			if not response_text.strip():
				return {}
			return json.loads(response_text)
	except error.HTTPError as exc:
		error_body = exc.read().decode("utf-8", errors="ignore")
		raise HTTPException(status_code=exc.code, detail=error_body or "search-service HTTP error") from exc
	except error.URLError as exc:
		raise HTTPException(status_code=502, detail=f"search-service unavailable: {exc.reason}") from exc
	except TimeoutError as exc:
		raise HTTPException(status_code=504, detail="search-service timeout") from exc
	except json.JSONDecodeError as exc:
		raise HTTPException(status_code=502, detail="search-service returned invalid JSON") from exc
