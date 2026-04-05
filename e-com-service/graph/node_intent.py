"""Intent detection node for query classification."""

import logging
import time

try:
	from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	HumanMessage = None
	SystemMessage = None

try:
	from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	ChatGoogleGenerativeAI = None

from core.config import settings
from graph.types import ChatState


logger = logging.getLogger(__name__)


def _rule_based_intent(query: str) -> tuple[str, str]:
	"""Fallback intent detection when LLM is unavailable."""
	query = query.lower().strip()

	rag_keywords = [
		"suggest", "recommend", "advice", "best", "good", "like",
		"similar", "compare", "feature", "specification", "what is",
		"tell me", "explain", "how is", "review"
	]
	db_keywords = [
		"stock", "price", "cost", "available", "in stock",
		"out of stock", "how much", "quantity", "inventory"
	]

	has_rag_keyword = any(kw in query for kw in rag_keywords)
	has_db_keyword = any(kw in query for kw in db_keywords)

	if has_db_keyword and has_rag_keyword:
		return "combine", "Câu hỏi chứa cả nhu cầu tư vấn và thông tin tồn kho/giá nên chọn combine."
	if has_db_keyword:
		return "db", "Câu hỏi tập trung vào giá, tồn kho hoặc số lượng nên chọn db."
	return "rag", "Câu hỏi thiên về kiến thức sản phẩm nên chọn rag."


def node_intent(state: ChatState) -> ChatState:
	"""
	Phân loại ý định của câu hỏi:
	- rag: hỏi tư vấn, gợi ý, so sánh, mô tả sản phẩm
	- db: hỏi giá, tồn kho, số lượng, khả dụng
	- combine: vừa cần tư vấn vừa cần dữ liệu thực tế
	"""
	started = time.perf_counter()
	query = state.get("query", "").strip()
	logger.info("[node_intent] start | user_id=%s | query=%s", state.get("user_id", ""), query[:120])
	logger.info("[node_intent] input | query_len=%d | existing_intent=%s", len(query), state.get("detected_intent"))

	if not query:
		state["detected_intent"], state["reasoning"] = "rag", "Câu hỏi trống nên mặc định chọn rag."
		logger.info("[node_intent] empty query -> intent=rag | elapsed=%.3fs", time.perf_counter() - started)
		return state

	if ChatGoogleGenerativeAI is None or not settings.GOOGLE_API_KEY or HumanMessage is None or SystemMessage is None:
		detected_intent, reason = _rule_based_intent(query)
		state["detected_intent"] = detected_intent
		state["reasoning"] = reason
		logger.info("[node_intent] rule-based intent=%s | reason=%s", detected_intent, reason)
		logger.info("[node_intent] end | elapsed=%.3fs", time.perf_counter() - started)
		return state

	try:
		llm = ChatGoogleGenerativeAI(
			model="models/gemini-3.1-flash-lite-preview",
			temperature=0,
			google_api_key=settings.GOOGLE_API_KEY or None,
		)

		messages = [
			SystemMessage(
				content=(
					"Bạn là bộ phân loại ý định cho chatbot thương mại điện tử. "
					"Hãy đọc câu hỏi của người dùng và chỉ trả về đúng một nhãn trong ba nhãn sau: rag, db, combine. "
					"Quy tắc: rag = tư vấn/gợi ý/so sánh/giải thích sản phẩm; db = hỏi giá/tồn kho/số lượng/trạng thái còn hàng; combine = vừa cần tư vấn vừa cần dữ liệu thực tế. "
					"Không giải thích, không thêm ký tự thừa, không thêm dấu ngoặc kép."
				)
			),
			HumanMessage(content=f"Câu hỏi: {query}")
		]

		response = llm.invoke(messages)
		label = (response.content if hasattr(response, "content") else str(response)).strip().lower()
		if "combine" in label:
			detected_intent = "combine"
		elif "db" in label:
			detected_intent = "db"
		else:
			detected_intent = "rag"

		state["detected_intent"] = detected_intent
		state["reasoning"] = f"LLM phân loại ý định là {detected_intent}."
		logger.info("[node_intent] llm intent=%s", detected_intent)

	except Exception as exc:
		detected_intent, reason = _rule_based_intent(query)
		state["detected_intent"] = detected_intent
		state["reasoning"] = reason
		logger.exception("[node_intent] llm classify failed, fallback rule-based | error=%s", exc)
	
	logger.info(
		"[node_intent] output | intent=%s | reasoning_len=%d",
		state.get("detected_intent"),
		len(str(state.get("reasoning", "") or "")),
	)
	logger.info("[node_intent] end | elapsed=%.3fs", time.perf_counter() - started)
	return state
