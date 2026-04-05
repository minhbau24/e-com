"""Combine node for merging results from multiple data sources."""

import logging
import time

from graph.types import ChatState
from services.combine_service import combine_contexts


logger = logging.getLogger(__name__)


def node_combine(state: ChatState) -> ChatState:
	"""
	Combine results from RAG and DB sources for hybrid queries.
	Formats context for final LLM answer generation.
	"""
	started = time.perf_counter()
	rag_context = state.get("rag_results", "") or ""
	db_context = state.get("db_results", {}) or {}
	logger.info(
		"[node_combine] start | rag_len=%d | db_keys=%s",
		len(str(rag_context)),
		list(db_context.keys()) if isinstance(db_context, dict) else [],
	)
	logger.info(
		"[node_combine] input | db_products=%d",
		len(db_context.get("items", [])) if isinstance(db_context, dict) else 0,
	)

	combined = combine_contexts(rag_context=rag_context, db_payload=db_context)
	
	state["reasoning"] += "\n✓ Combined KB + DB contexts for answer generation"
	state["rag_results"] = combined  # Store combined context in rag_results for downstream
	logger.info("[node_combine] output | combined_preview=%s", str(combined)[:160])
	logger.info("[node_combine] end | combined_len=%d | elapsed=%.3fs", len(str(combined)), time.perf_counter() - started)
	
	return state
