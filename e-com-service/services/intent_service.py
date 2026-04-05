"""Intent detection service wrapper."""

from __future__ import annotations

from typing import Dict

from graph.node_intent import node_intent
from graph.types import ChatState


def detect_intent(query: str, user_id: str = "system") -> Dict[str, str]:
	"""Run intent node and return intent plus reasoning."""
	state: ChatState = {
		"user_id": user_id,
		"query": query,
		"detected_intent": None,
		"rag_results": None,
		"db_results": None,
		"reasoning": "",
		"response": "",
	}
	state = node_intent(state)
	return {
		"intent": state.get("detected_intent", "rag") or "rag",
		"reasoning": state.get("reasoning", ""),
	}
