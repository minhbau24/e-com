"""Output node for generating final response using LLM."""

import logging
import time

try:
	from langchain_core.messages import HumanMessage  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	HumanMessage = None

try:
	from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	ChatGoogleGenerativeAI = None

from utils.config import settings
from graph.types import ChatState


logger = logging.getLogger(__name__)


def node_output(state: ChatState) -> ChatState:
	"""
	Generate final response using LLM with context from RAG/DB.
	Uses Google Generative AI (Gemini) for answer generation.
	"""
	started = time.perf_counter()
	query = state.get("query", "")
	intent = str(state.get("detected_intent", "") or "")
	rag_context = state.get("rag_results")
	db_results = state.get("db_results", {}) or {}
	db_context = db_results.get("context", "") if isinstance(db_results, dict) else ""

	if intent == "db":
		context = db_context or rag_context or ""
		context_source = "db"
	elif intent == "combine":
		context = rag_context or db_context or ""
		context_source = "combine"
	else:
		context = rag_context or db_context or ""
		context_source = "rag"

	if context is None:
		context = ""
	context_text = str(context)
	reasoning = state.get("reasoning", "")
	logger.info(
		"[node_output] start | query=%s | intent=%s | context_source=%s | context_len=%d",
		str(query)[:120],
		intent,
		context_source,
		len(context_text),
	)
	logger.info(
		"[node_output] input | query_len=%d | reasoning_len=%d | context_preview=%s",
		len(str(query or "")),
		len(str(reasoning or "")),
		context_text[:160],
	)
	
	try:
		if ChatGoogleGenerativeAI is None:
			state["response"] = "[Error] LangChain Google GenAI not installed"
			logger.warning("[node_output] missing langchain_google_genai")
			logger.info("[node_output] end | elapsed=%.3fs", time.perf_counter() - started)
			return state
		
		if not settings.GOOGLE_API_KEY:
			state["response"] = "[Error] GOOGLE_API_KEY not configured"
			logger.warning("[node_output] GOOGLE_API_KEY missing")
			logger.info("[node_output] end | elapsed=%.3fs", time.perf_counter() - started)
			return state
		
		# Initialize LLM
		llm = ChatGoogleGenerativeAI(
			model="models/gemini-3.1-flash-lite-preview",
			google_api_key=settings.GOOGLE_API_KEY,
			temperature=0,
		)
		
		# Build prompt with context
		system_prompt = """Bạn là trợ lý tư vấn sản phẩm cho hệ thống thương mại điện tử.
        Hãy trả lời hoàn toàn bằng tiếng Việt, ngắn gọn, rõ ràng và thực tế.
        Ưu tiên sử dụng ngữ cảnh từ kho tri thức được cung cấp.
        Nếu ngữ cảnh không đủ, hãy nói rõ phần nào chưa chắc chắn thay vì bịa ra thông tin.
        Không nhắc tới nội dung nội bộ của hệ thống, không giải thích quy trình suy luận."""
		
		user_prompt = f"""Câu hỏi của khách hàng: {query}

        Ngữ cảnh từ kho tri thức:
		{context_text if context_text else '[Không có ngữ cảnh]'}

        Lý do định tuyến nội bộ:
        {reasoning if reasoning else '[Không có]'}

        Hãy trả lời khách hàng một cách hữu ích, ngắn gọn và đúng trọng tâm."""
		
		# Generate response
		messages = [
			HumanMessage(content=f"{system_prompt}\n\n{user_prompt}")
			if HumanMessage else None
		]
		
		if messages[0] is None:
			state["response"] = "[Error] LangChain message types not available"
			logger.warning("[node_output] message type unavailable")
		else:
			llm_started = time.perf_counter()
			response = llm.invoke(messages)
			state["response"] = response.content if hasattr(response, 'content') else str(response)
			state["reasoning"] += "\n✓ Generated response with LLM"
			logger.info(
				"[node_output] generated | llm_elapsed=%.3fs | response_len=%d | response_preview=%s",
				time.perf_counter() - llm_started,
				len(str(state.get("response", ""))),
				str(state.get("response", ""))[:160],
			)
		
	except Exception as e:
		state["response"] = f"[Error] {str(e)}"
		state["reasoning"] += f"\n✗ LLM error: {str(e)}"
		logger.exception("[node_output] llm error | error=%s", e)
	
	logger.info("[node_output] end | elapsed=%.3fs", time.perf_counter() - started)
	return state
