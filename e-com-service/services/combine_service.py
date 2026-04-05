"""Utilities for combining context from KB and DB sources."""

from __future__ import annotations

from typing import Any, Dict


def combine_contexts(rag_context: str, db_payload: Dict[str, Any] | None) -> str:
	"""Merge context blocks for final answer generation."""
	db_payload = db_payload or {}
	return (
		"KB Context (từ kho tri thức):\n"
		f"{rag_context or '[Không có KB context]'}\n\n"
		"DB Context (dữ liệu realtime):\n"
		f"{db_payload if db_payload else '[Không có DB context]'}"
	)
