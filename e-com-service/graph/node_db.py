"""Database query node for real-time product data."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict

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
from services.db_service import format_products_for_context, search_products_advanced


logger = logging.getLogger(__name__)


def _amount_to_vnd(raw_number: str, unit: str | None) -> int:
	number = float(raw_number.replace(",", "."))
	unit = (unit or "").lower()
	if unit in {"k", "ngan", "nghin"}:
		number *= 1_000
	elif unit in {"tr", "trieu", "m"}:
		number *= 1_000_000
	return int(number)


def _extract_price_filters(text: str) -> Dict[str, Any]:
	filters: Dict[str, Any] = {}

	range_match = re.search(
		r"(?:tu\s*|từ\s*)(\d+(?:[.,]\d+)?)\s*(k|ngan|nghin|tr|trieu|m)?\s*(?:den|đến|to|-)\s*(\d+(?:[.,]\d+)?)\s*(k|ngan|nghin|tr|trieu|m)?",
		text,
		re.IGNORECASE,
	)
	if range_match:
		price_min = _amount_to_vnd(range_match.group(1), range_match.group(2))
		price_max = _amount_to_vnd(range_match.group(3), range_match.group(4))
		filters["price_min"] = min(price_min, price_max)
		filters["price_max"] = max(price_min, price_max)
		return filters

	max_match = re.search(
		r"(?:duoi|dưới|toi da|tối đa|max|<=|<)\s*(\d+(?:[.,]\d+)?)\s*(k|ngan|nghin|tr|trieu|m)?",
		text,
		re.IGNORECASE,
	)
	if max_match:
		filters["price_max"] = _amount_to_vnd(max_match.group(1), max_match.group(2))

	min_match = re.search(
		r"(?:tren|trên|tu|từ|min|>=|>)\s*(\d+(?:[.,]\d+)?)\s*(k|ngan|nghin|tr|trieu|m)?",
		text,
		re.IGNORECASE,
	)
	if min_match:
		filters["price_min"] = _amount_to_vnd(min_match.group(1), min_match.group(2))

	return filters


def _extract_sort(text: str) -> Dict[str, Any]:
	lower = text.lower()
	if any(key in lower for key in ["đánh giá cao", "rating cao", "tot nhat", "tốt nhất"]):
		return {"field": "rating", "order": "desc"}
	if any(key in lower for key in ["rẻ nhất", "re nhat", "giá thấp", "gia thap"]):
		return {"field": "price", "order": "asc"}
	if any(key in lower for key in ["đắt nhất", "dat nhat", "giá cao", "gia cao"]):
		return {"field": "price", "order": "desc"}
	return {"field": "relevance", "order": "desc"}


def _extract_limit(text: str, default_limit: int = 5) -> int:
	match = re.search(r"(?:top|lấy|lay|hien thi|hiển thị)\s*(\d{1,2})", text, re.IGNORECASE)
	if match:
		return max(1, min(20, int(match.group(1))))
	return default_limit


def _extract_in_stock(text: str) -> bool | None:
	lower = text.lower()
	if any(key in lower for key in ["còn hàng", "con hang", "in stock", "available"]):
		return True
	if any(key in lower for key in ["hết hàng", "het hang", "out of stock"]):
		return False
	return None


def _clean_query_for_search(text: str) -> str:
	cleaned = text
	for pattern in [
		r"(?:duoi|dưới|toi da|tối đa|max|<=|<)\s*\d+(?:[.,]\d+)?\s*(?:k|ngan|nghin|tr|trieu|m)?",
		r"(?:tren|trên|tu|từ|min|>=|>)\s*\d+(?:[.,]\d+)?\s*(?:k|ngan|nghin|tr|trieu|m)?",
		r"(?:tu\s*|từ\s*)\d+(?:[.,]\d+)?\s*(?:k|ngan|nghin|tr|trieu|m)?\s*(?:den|đến|to|-)\s*\d+(?:[.,]\d+)?\s*(?:k|ngan|nghin|tr|trieu|m)?",
		r"(?:top|lấy|lay|hien thi|hiển thị)\s*\d{1,2}",
		r"(?:còn hàng|con hang|in stock|available|hết hàng|het hang|out of stock)",
		r"(?:rẻ nhất|re nhat|đắt nhất|dat nhat|giá thấp|gia thap|giá cao|gia cao|đánh giá cao|rating cao)",
	]:
		cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

	cleaned = " ".join(cleaned.split())
	return cleaned or text


def _normalize_query_token(text: str) -> str:
	"""Normalize short free-text query to detect generic, low-signal terms."""
	value = (text or "").strip().lower()
	value = re.sub(r"[^\w\s]", " ", value)
	value = " ".join(value.split())
	return value


def _build_search_request(query: str) -> Dict[str, Any]:
	cleaned_query = _clean_query_for_search(query)
	filters = _extract_price_filters(query)
	in_stock = _extract_in_stock(query)
	if in_stock is not None:
		filters["in_stock"] = in_stock

	limit = _extract_limit(query, default_limit=5)
	sort = _extract_sort(query)

	return {
		"query": cleaned_query,
		"filters": filters,
		"sort": sort,
		"pagination": {"page": 1, "size": limit},
	}


def _sanitize_search_request(raw: Dict[str, Any], fallback_query: str) -> Dict[str, Any]:
	"""Validate/normalize extracted payload before calling search-service."""
	allowed_filter_fields = {
		"price_min",
		"price_max",
		"author",
		"publisher",
		"publication_year_min",
		"publication_year_max",
		"language",
		"cover_type",
		"page_count_min",
		"page_count_max",
		"in_stock",
	}
	allowed_sort_fields = {
		"relevance",
		"price",
		"rating",
		"review_count",
		"stock",
		"created_at",
		"publication_year",
		"page_count",
		"name",
	}

	query = str(raw.get("query", "")).strip() or _clean_query_for_search(fallback_query)

	filters_raw = raw.get("filters", {}) if isinstance(raw.get("filters"), dict) else {}
	filters: Dict[str, Any] = {}
	for key, value in filters_raw.items():
		if key not in allowed_filter_fields or value in (None, ""):
			continue
		filters[key] = value

	# If LLM returns a generic query like "sach" while structured filters are present,
	# prioritize filters to avoid low-signal keyword matching.
	normalized_query = _normalize_query_token(query)
	generic_query_terms = {"sach", "sách", "book", "books", "san pham", "sản phẩm", "product", "products"}
	has_text_filter = bool(filters.get("author") or filters.get("publisher") or filters.get("language") or filters.get("cover_type"))
	if normalized_query in generic_query_terms and has_text_filter:
		query = ""

	sort_raw = raw.get("sort", {}) if isinstance(raw.get("sort"), dict) else {}
	sort_field = sort_raw.get("field", "relevance")
	if sort_field not in allowed_sort_fields:
		sort_field = "relevance"
	sort_order = str(sort_raw.get("order", "desc")).lower()
	if sort_order not in {"asc", "desc"}:
		sort_order = "desc"

	pagination_raw = raw.get("pagination", {}) if isinstance(raw.get("pagination"), dict) else {}
	page = pagination_raw.get("page", 1)
	size = pagination_raw.get("size", 5)
	try:
		page = int(page)
	except Exception:
		page = 1
	try:
		size = int(size)
	except Exception:
		size = 5
	page = max(1, page)
	size = max(1, min(20, size))

	return {
		"query": query,
		"filters": filters,
		"sort": {"field": sort_field, "order": sort_order},
		"pagination": {"page": page, "size": size},
	}


def _extract_json_block(text: str) -> Dict[str, Any] | None:
	text = text.strip()
	try:
		obj = json.loads(text)
		return obj if isinstance(obj, dict) else None
	except json.JSONDecodeError:
		pass

	match = re.search(r"\{.*\}", text, flags=re.DOTALL)
	if not match:
		return None
	try:
		obj = json.loads(match.group(0))
		return obj if isinstance(obj, dict) else None
	except json.JSONDecodeError:
		return None


def _build_search_request_with_llm(query: str) -> Dict[str, Any]:
	"""Use LLM to parse user query into search-service payload; fallback to regex."""
	if (
		ChatGoogleGenerativeAI is None
		or HumanMessage is None
		or SystemMessage is None
		or not settings.GOOGLE_API_KEY
	):
		return _build_search_request(query)

	prompt_schema = {
		"query": "string - bắt buộc là từ khóa phân biệt; nếu chỉ còn từ chung hoặc thông tin đã nằm trong filters thì phải để chuỗi rỗng ''",
		"filters": {
			"price_min": "int?",
			"price_max": "int?",
			"author": "string?",
			"publisher": "string?",
			"publication_year_min": "int?",
			"publication_year_max": "int?",
			"language": "string?",
			"cover_type": "string?",
			"page_count_min": "int?",
			"page_count_max": "int?",
			"in_stock": "bool?",
		},
		"sort": {"field": "relevance|price|rating|review_count|stock|created_at|publication_year|page_count|name", "order": "asc|desc"},
		"pagination": {"page": "int", "size": "int <= 20"},
	}

	system_prompt = (
		"Bạn là bộ trích xuất tham số tìm kiếm sản phẩm. "
		"Nhiệm vụ: chuyển câu người dùng thành JSON hợp lệ theo schema. "
		"Chỉ trả về JSON object, không markdown, không giải thích. "
		"Nếu không rõ thông tin thì bỏ trường đó, không suy diễn. "
		"QUY TẮC CỨNG cho field query: chỉ giữ từ khóa có tính phân biệt (chủ đề/đặc tính cụ thể). "
		"Tuyệt đối KHÔNG để query là các từ chung như: 'sách', 'book', 'sản phẩm', 'hàng', 'cho tôi', 'tác giả', 'của'. "
		"Nếu filters đã có author/publisher/language/cover_type và phần còn lại không có từ khóa phân biệt, query PHẢI là ''. "
		"Nếu query trùng hoặc gần trùng với giá trị trong filters (ví dụ tên tác giả), query PHẢI là ''. "
		"Mọi output vi phạm các quy tắc trên được xem là sai."
	)
	user_prompt = (
		f"Query: {query}\n"
		f"Schema: {json.dumps(prompt_schema, ensure_ascii=False)}\n"
	)

	try:
		llm = ChatGoogleGenerativeAI(
			model="models/gemini-3.1-flash-lite-preview",
			google_api_key=settings.GOOGLE_API_KEY,
			temperature=0,
		)
		response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
		content = response.content if hasattr(response, "content") else str(response)
		parsed = _extract_json_block(content)
		if isinstance(parsed, dict):
			return _sanitize_search_request(parsed, fallback_query=query)
	except Exception:
		pass

	return _build_search_request(query)


def node_db(state: ChatState) -> ChatState:
	"""
	Query database for real-time inventory/pricing/product data.
	This stub will be extended with actual db_service.py calls.
	
	TODO: Integrate with services/db_service.py once implemented.
	"""
	started = time.perf_counter()
	query = state.get("query", "")
	logger.info("[node_db] start | query=%s", str(query)[:160])
	logger.info("[node_db] input | query_len=%d", len(str(query or "")))
	
	try:
		request_started = time.perf_counter()
		search_request = _build_search_request_with_llm(query)
		logger.info(
			"[node_db] request_built | elapsed=%.3fs | query=%s | filters=%s | sort=%s | page=%s",
			time.perf_counter() - request_started,
			search_request.get("query"),
			search_request.get("filters"),
			search_request.get("sort"),
			search_request.get("pagination"),
		)
		search_started = time.perf_counter()
		products = search_products_advanced(
			query=search_request["query"],
			filters=search_request["filters"],
			sort=search_request["sort"],
			pagination=search_request["pagination"],
			limit=int(search_request["pagination"]["size"]),
		)
		logger.info("[node_db] search_service done | elapsed=%.3fs", time.perf_counter() - search_started)
		db_results = {
			"query": query,
			"search_request": search_request,
			"count": len(products),
			"items": products,
			"context": format_products_for_context(products),
		}

		state["db_results"] = db_results
		if products:
			state["reasoning"] += f"\n✓ DB trả về {len(products)} sản phẩm phù hợp"
			state["reasoning"] += f"\n• search_request={search_request}"
			logger.info(
				"[node_db] output | products=%d | context_len=%d",
				len(products),
				len(str(db_results.get("context", "") or "")),
			)
		else:
			state["reasoning"] += "\n✗ DB không có sản phẩm phù hợp"
			logger.info("[node_db] no products found")
		
	except Exception as e:
		state["db_results"] = {"error": str(e)}
		state["reasoning"] += f"\n✗ DB error: {str(e)}"
		logger.exception("[node_db] error | error=%s", e)
	
	logger.info("[node_db] end | elapsed=%.3fs", time.perf_counter() - started)
	return state
