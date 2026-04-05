"""Routing logic for LangGraph conditional edges."""

import logging

from graph.types import ChatState


logger = logging.getLogger(__name__)


def route_by_intent(state: ChatState) -> str:
	"""
	Route to appropriate node based on detected intent.
	- 'rag': Direct to KB retrieval
	- 'db': Direct to database
	- 'combine': Execute both, then merge
	"""
	intent = state.get("detected_intent", "rag")
	user_id = state.get("user_id", "")
	query_preview = str(state.get("query", ""))[:120]

	if intent == "rag":
		next_node = "rag_node"
	elif intent == "combine":
		next_node = "combine_start"
	else:  # db
		next_node = "db_node"

	logger.info(
		"[route_by_intent] user_id=%s | intent=%s | next=%s | query=%s",
		user_id,
		intent,
		next_node,
		query_preview,
	)
	return next_node


def route_after_rag(state: ChatState) -> str:
	"""Route after RAG: go to output or combine if needed."""
	intent = state.get("detected_intent", "rag")
	next_node = "combine" if intent == "combine" else "output"
	logger.info(
		"[route_after_rag] intent=%s | next=%s | rag_len=%d",
		intent,
		next_node,
		len(str(state.get("rag_results", "") or "")),
	)
	return next_node


def route_after_db(state: ChatState) -> str:
	"""Route after DB: go to output or combine if needed."""
	intent = state.get("detected_intent", "db")
	next_node = "combine" if intent == "combine" else "output"
	db_result = state.get("db_results", {}) or {}
	product_count = len(db_result.get("items", [])) if isinstance(db_result, dict) else 0
	logger.info(
		"[route_after_db] intent=%s | next=%s | db_products=%d",
		intent,
		next_node,
		product_count,
	)
	return next_node
