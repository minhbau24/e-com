"""LangGraph definition for e-commerce chatbot orchestration.

Builds a stateful graph that routes queries through intent detection,
retrieval (RAG), database lookup, and answer generation.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from langgraph.graph import StateGraph, END  # type: ignore[import-not-found]


from graph.nodes import (
	ChatState,
	node_intent,
	node_rag,
	node_db,
	node_combine,
	node_output,
	route_by_intent,
	route_after_rag,
	route_after_db,
)


logger = logging.getLogger(__name__)


def _snapshot_state(state: ChatState) -> str:
	"""Build a concise state snapshot for detailed runtime logs."""
	db_result = state.get("db_results", {}) or {}
	product_count = len(db_result.get("items", [])) if isinstance(db_result, dict) else 0
	return (
		"user_id={user_id} | intent={intent} | query_len={query_len} | rag_len={rag_len} "
		"| db_products={db_products} | reasoning_len={reasoning_len} | response_len={response_len}"
	).format(
		user_id=state.get("user_id", ""),
		intent=state.get("detected_intent"),
		query_len=len(str(state.get("query", "") or "")),
		rag_len=len(str(state.get("rag_results", "") or "")),
		db_products=product_count,
		reasoning_len=len(str(state.get("reasoning", "") or "")),
		response_len=len(str(state.get("response", "") or "")),
	)


def build_chat_graph() -> Optional[StateGraph]:
	"""
	Build LangGraph state machine for chatbot.
	
	Flow:
	1. Detect intent (rag/db/combine)
	2. Route to RAG and/or DB based on intent
	3. Optionally combine results
	4. Generate final response
	
	Returns:
		StateGraph object or None if LangGraph not installed
	
	Example:
		>>> graph = build_chat_graph()
		>>> state = {"user_id": "user1", "query": "recommend products", ...}
		>>> result = graph.invoke(state)
		>>> print(result["response"])
	"""
	
	if StateGraph is None or END is None:
		return None
	
	# Initialize graph
	graph = StateGraph(ChatState)
	
	# ========================================================================
	# Add Nodes
	# ========================================================================
	graph.add_node("intent", node_intent)
	graph.add_node("rag_node", node_rag)
	graph.add_node("db_node", node_db)
	graph.add_node("combine", node_combine)
	graph.add_node("output", node_output)
	
	# ========================================================================
	# Add Edges and Routing
	# ========================================================================
	
	# Entry point
	graph.set_entry_point("intent")
	
	# Main routing after intent detection
	graph.add_conditional_edges(
		"intent",
		route_by_intent,
		{
			"rag_node": "rag_node",
			"db_node": "db_node",
			"combine_start": "rag_node",  # Start combine flow with RAG first
		},
	)
	
	# After RAG retrieval
	graph.add_conditional_edges(
		"rag_node",
		route_after_rag,
		{
			"output": "output",
			"combine": "db_node",  # If combining, fetch DB data next
		},
	)
	
	# After DB lookup
	graph.add_conditional_edges(
		"db_node",
		route_after_db,
		{
			"output": "output",
			"combine": "combine",  # If combining, merge results
		},
	)
	
	# After combining results
	graph.add_edge("combine", "output")
	
	# Final output is the exit point
	graph.add_edge("output", END)
	
	# ========================================================================
	# Compile graph
	# ========================================================================
	return graph.compile()


def invoke_chat(query: str, user_id: str = "default", debug: bool = False) -> dict:
	"""
	Execute chat flow end-to-end.
	
	Args:
		query: User question/request
		user_id: Unique user identifier
		debug: Whether to include reasoning logs
	
	Returns:
		Dictionary with response and optional debug info
	
	Example:
		>>> result = invoke_chat("suggest best phone under 1000")
		>>> print(result["response"])
	"""
	
	started = time.perf_counter()
	logger.info("[invoke_chat] start | user_id=%s | query=%s", user_id, query[:160])
	logger.info("[invoke_chat] input | user_id=%s | debug=%s | query_len=%d", user_id, debug, len(query))
	graph = build_chat_graph()
	if graph is None:
		logger.error("[invoke_chat] graph unavailable (langgraph not installed)")
		return {
			"error": "LangGraph not installed. Install langraph package.",
			"response": None,
		}
	
	# Initialize state
	initial_state: ChatState = {
		"user_id": user_id,
		"query": query,
		"detected_intent": None,
		"rag_results": None,
		"db_results": None,
		"reasoning": "",
		"response": "",
	}
	logger.info("[invoke_chat] state.init | %s", _snapshot_state(initial_state))
	
	try:
		# Execute graph
		invoke_started = time.perf_counter()
		logger.info("[invoke_chat] graph.invoke begin")
		final_state = graph.invoke(initial_state)
		logger.info(
			"[invoke_chat] graph.invoke done | elapsed=%.3fs | %s",
			time.perf_counter() - invoke_started,
			_snapshot_state(final_state),
		)
		
		# Build result
		result = {
			"user_id": final_state.get("user_id"),
			"query": final_state.get("query"),
			"response": final_state.get("response", ""),
			"intent": final_state.get("detected_intent"),
		}
		
		if debug:
			result["debug"] = {
				"reasoning": final_state.get("reasoning", ""),
				"rag_results": final_state.get("rag_results"),
				"db_results": final_state.get("db_results"),
			}

		logger.info(
			"[invoke_chat] output | user_id=%s | intent=%s | response_preview=%s",
			result.get("user_id"),
			result.get("intent"),
			str(result.get("response", ""))[:160],
		)
		
		logger.info("[invoke_chat] success | elapsed=%.3fs", time.perf_counter() - started)
		return result
		
	except Exception as e:
		logger.exception("[invoke_chat] failed | elapsed=%.3fs | error=%s", time.perf_counter() - started, e)
		return {
			"error": str(e),
			"response": f"[Error processing query] {str(e)}",
		}


if __name__ == "__main__":
	# Test the graph
	test_queries = [
		"recommend best laptop for programming",
		"what's the price of iPhone 15?",
		"suggest phone with good camera that's in stock",
	]
	
	for test_query in test_queries:
		print(f"\n{'='*60}")
		print(f"Query: {test_query}")
		print(f"{'='*60}")
		
		result = invoke_chat(test_query, debug=True)
		
		print(f"Intent: {result.get('intent')}")
		print(f"\nResponse:\n{result.get('response')}")
		
		if "debug" in result:
			print(f"\nReasoning:\n{result['debug']['reasoning']}")
