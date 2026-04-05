"""RAG (Retrieval-Augmented Generation) node for knowledge base queries."""

import logging
import time

from core.config import settings
from graph.types import ChatState
from kb.retriever import create_langgraph_retriever_tool


logger = logging.getLogger(__name__)


def _execute_retriever_tool(retriever_tool, query: str, top_k: int = 5):
	"""Execute retriever tool for both StructuredTool and plain callable forms."""
	if hasattr(retriever_tool, "invoke"):
		return retriever_tool.invoke({"query": query, "top_k": top_k})
	return retriever_tool(query=query, top_k=top_k)


def node_rag(state: ChatState) -> ChatState:
	"""
	Query knowledge base using retriever tool.
	Retrieves relevant product chunks and builds context for LLM.
	"""
	started = time.perf_counter()
	query = state.get("query", "")
	logger.info("[node_rag] start | query=%s", str(query)[:120])
	logger.info("[node_rag] input | query_len=%d | backend=%s", len(str(query or "")), settings.KB_RETRIEVER_BACKEND)
	if not query:
		state["rag_results"] = ""
		logger.info("[node_rag] empty query, skip retrieval | elapsed=%.3fs", time.perf_counter() - started)
		return state
	
	try:
		# Create retriever tool with LangGraph compatibility
		retriever_tool = create_langgraph_retriever_tool(
			name="kb_retriever",
			backend=settings.KB_RETRIEVER_BACKEND,
		)
		
		# Execute retrieval with fallback
		try:
			retrieval_started = time.perf_counter()
			rag_results = _execute_retriever_tool(retriever_tool, query=query, top_k=5)
			logger.info("[node_rag] retriever call done | elapsed=%.3fs", time.perf_counter() - retrieval_started)
		except Exception as retrieval_error:
			rag_results = f"[Retrieval Error] {str(retrieval_error)}"
			logger.exception("[node_rag] retriever failed | error=%s", retrieval_error)
		
		state["rag_results"] = rag_results
		
		# Log reasoning
		if rag_results:
			state["reasoning"] += f"\n✓ Retrieved {rag_results.count('[') if rag_results else 0} KB chunks"
			logger.info("[node_rag] output | rag_len=%d | rag_preview=%s", len(str(rag_results)), str(rag_results)[:160])
		else:
			state["reasoning"] += "\n✗ No KB results found"
			logger.info("[node_rag] no kb results")
			
	except Exception as e:
		state["rag_results"] = f"[RAG Error] {str(e)}"
		state["reasoning"] += f"\n✗ RAG pipeline error: {str(e)}"
		logger.exception("[node_rag] pipeline error | error=%s", e)
	
	logger.info("[node_rag] end | elapsed=%.3fs", time.perf_counter() - started)
	return state
