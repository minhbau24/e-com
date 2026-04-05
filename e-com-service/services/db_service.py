"""Database-like service that prefers search-service and falls back to local CSV."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request as urlrequest

import pandas as pd

from utils.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCT_CSV = PROJECT_ROOT / "data" / "product.csv"

_PRODUCT_DF: pd.DataFrame | None = None


def _load_products() -> pd.DataFrame:
	global _PRODUCT_DF
	if _PRODUCT_DF is not None:
		return _PRODUCT_DF

	if not DEFAULT_PRODUCT_CSV.exists():
		raise FileNotFoundError(f"Product data not found: {DEFAULT_PRODUCT_CSV}")

	df = pd.read_csv(DEFAULT_PRODUCT_CSV)
	for col in ["name", "short_description", "description"]:
		if col in df.columns:
			df[col] = df[col].fillna("").astype(str)

	if "price" in df.columns:
		df["price"] = pd.to_numeric(df["price"], errors="coerce")
	if "stock" in df.columns:
		df["stock"] = pd.to_numeric(df["stock"], errors="coerce")
	if "rating_average" in df.columns:
		df["rating_average"] = pd.to_numeric(df["rating_average"], errors="coerce")

	_PRODUCT_DF = df
	return _PRODUCT_DF


def _to_product_record(row: pd.Series) -> Dict[str, Any]:
	stock = int(row.get("stock", 0) or 0)
	price = float(row.get("price", 0.0) or 0.0)
	rating = float(row.get("rating_average", 0.0) or 0.0)
	return {
		"id": str(row.get("id", "")),
		"name": str(row.get("name", "")),
		"price": price,
		"stock": stock,
		"is_available": stock > 0,
		"rating": rating,
	}


def _to_product_record_from_search_service(item: Dict[str, Any]) -> Dict[str, Any]:
	stock = int(item.get("stock", 0) or 0)
	price = float(item.get("price", 0.0) or 0.0)
	rating = float(item.get("rating", 0.0) or 0.0)
	return {
		"id": str(item.get("product_id", "")),
		"name": str(item.get("name", "")),
		"price": price,
		"stock": stock,
		"is_available": stock > 0,
		"rating": rating,
	}


def _build_search_payload(query: str, limit: int) -> Dict[str, Any]:
	return {
		"query": query,
		"filters": {},
		"sort": {"field": "relevance", "order": "desc"},
		"pagination": {"page": 1, "size": max(1, min(limit, settings.SEARCH_SERVICE_MAX_PAGE_SIZE))},
	}


def _search_products_via_service_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
	if not settings.SEARCH_SERVICE_URL:
		return []

	body = json.dumps(payload).encode("utf-8")

	req = urlrequest.Request(
		settings.SEARCH_SERVICE_URL,
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)

	with urlrequest.urlopen(req, timeout=settings.SEARCH_SERVICE_TIMEOUT_SECONDS) as resp:
		status = getattr(resp, "status", 200)
		if status >= 400:
			raise RuntimeError(f"search-service returned HTTP {status}")
		data = json.loads(resp.read().decode("utf-8"))

	items = data.get("items", []) if isinstance(data, dict) else []
	return [_to_product_record_from_search_service(item) for item in items]


def _search_products_via_service(query: str, limit: int) -> List[Dict[str, Any]]:
	payload = _build_search_payload(query=query, limit=limit)
	return _search_products_via_service_payload(payload)


def _search_products_from_csv(query: str, limit: int) -> List[Dict[str, Any]]:
	"""Fallback search against local CSV if search-service is unavailable."""
	df = _load_products()
	text = query.strip().lower()
	if not text:
		return []

	name_match = df["name"].str.lower().str.contains(text, na=False)
	short_match = df["short_description"].str.lower().str.contains(text, na=False)
	desc_match = df["description"].str.lower().str.contains(text, na=False)

	candidates = df[name_match | short_match | desc_match].copy()
	if candidates.empty:
		return []

	candidates = candidates.sort_values(by=["stock", "rating_average"], ascending=[False, False])
	rows = candidates.head(max(1, limit)).to_dict(orient="records")
	return [_to_product_record(pd.Series(item)) for item in rows]


def search_products(query: str, limit: int = 5) -> List[Dict[str, Any]]:
	"""Search products for DB node/recommend endpoint via search-service first."""
	text = query.strip()
	if not text:
		return []

	try:
		results = _search_products_via_service(query=text, limit=limit)
		if results:
			return results
	except (error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError):
		pass

	return _search_products_from_csv(query=text, limit=limit)


def search_products_advanced(
	query: str,
	filters: Dict[str, Any] | None = None,
	sort: Dict[str, Any] | None = None,
	pagination: Dict[str, Any] | None = None,
	limit: int = 5,
) -> List[Dict[str, Any]]:
	"""Structured search for chatbot node using search-service payload shape."""
	text = query.strip()
	if not text:
		return []

	size = max(1, min(limit, settings.SEARCH_SERVICE_MAX_PAGE_SIZE))
	paging = {"page": 1, "size": size}
	if isinstance(pagination, dict):
		if isinstance(pagination.get("page"), int) and pagination["page"] > 0:
			paging["page"] = pagination["page"]
		if isinstance(pagination.get("size"), int) and pagination["size"] > 0:
			paging["size"] = min(pagination["size"], settings.SEARCH_SERVICE_MAX_PAGE_SIZE)

	payload = {
		"query": text,
		"filters": filters or {},
		"sort": sort or {"field": "relevance", "order": "desc"},
		"pagination": paging,
	}

	try:
		results = _search_products_via_service_payload(payload)
		if results:
			return results
	except (error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError):
		pass

	fallback_limit = int(paging.get("size", limit) or limit)
	return _search_products_from_csv(query=text, limit=fallback_limit)


def format_products_for_context(products: List[Dict[str, Any]]) -> str:
	"""Format product records into compact Vietnamese context text."""
	if not products:
		return "[Không tìm thấy dữ liệu sản phẩm phù hợp trong DB]"

	lines: List[str] = []
	for idx, product in enumerate(products, start=1):
		availability = "còn hàng" if product.get("is_available") else "hết hàng"
		lines.append(
			f"[{idx}] {product.get('name')} | giá={int(product.get('price', 0))} | "
			f"tồn kho={product.get('stock', 0)} ({availability}) | rating={product.get('rating', 0):.1f}"
		)
	return "\n".join(lines)
