"""Tracking API routes.

Behavior tracking is intentionally disabled in this build variant.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/track", tags=["track"])


class TrackRequest(BaseModel):
	user_id: str = Field(..., min_length=1)
	event: str = Field(..., min_length=1)
	payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("")
def track(_request: TrackRequest) -> Dict[str, str]:
	return {
		"status": "disabled",
		"message": "Behavior tracking is excluded in this build.",
	}
