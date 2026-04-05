"""State and type definitions for LangGraph chatbot."""

from typing import Any, Dict, Optional, TypedDict


class ChatState(TypedDict):
	"""State object passed through LangGraph nodes."""
	user_id: str
	query: str
	detected_intent: Optional[str]  # "rag", "db", "combine"
	rag_results: Optional[str]  # KB retrieval context
	db_results: Optional[Dict[str, Any]]  # Database query results
	reasoning: str  # Internal reasoning log
	response: str  # Final response to user
