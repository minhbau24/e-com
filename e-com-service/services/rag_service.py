"""Service facade for chat orchestration via LangGraph."""

from __future__ import annotations

from typing import Any, Dict

from graph.graph import invoke_chat


def run_chat(query: str, user_id: str = "anonymous", debug: bool = False) -> Dict[str, Any]:
	"""Execute full graph flow and return unified payload for API responses."""
	return invoke_chat(query=query, user_id=user_id, debug=debug)
