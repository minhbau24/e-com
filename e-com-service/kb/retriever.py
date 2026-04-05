"""Retriever layer with PostgreSQL pgvector backend and JSON fallback."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
	import psycopg2  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	psycopg2 = None

try:
	from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	GoogleGenerativeAIEmbeddings = None

try:
	from langchain_core.tools import tool as langchain_tool  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
	langchain_tool = None

from core.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMBEDDINGS_PATH = PROJECT_ROOT / "kb" / "embeddings" / "embeddings.json"
EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"


@dataclass
class RetrievalResult:
	doc_id: str
	chunk_id: str
	chunk_index: int
	text: str
	score: float
	metadata: Dict[str, Any]

	def to_dict(self) -> Dict[str, Any]:
		return {
			"doc_id": self.doc_id,
			"chunk_id": self.chunk_id,
			"chunk_index": self.chunk_index,
			"text": self.text,
			"score": self.score,
			"metadata": self.metadata,
		}


class BaseEmbeddingRetriever:
	def __init__(self, embedding_model: Any = None) -> None:
		self.embedding_model = embedding_model or self._build_embedding_model()

	@staticmethod
	def _build_embedding_model() -> Any:
		if GoogleGenerativeAIEmbeddings is None:
			raise ImportError(
				"langchain_google_genai is required for query embeddings. Install it before using retriever."
			)

		return GoogleGenerativeAIEmbeddings(
			model=EMBEDDING_MODEL_NAME,
			google_api_key=settings.GOOGLE_API_KEY or None,
		)

	def _embed_query(self, query: str) -> List[float]:
		text = query.strip()
		if not text:
			raise ValueError("Query must not be empty.")
		return self.embedding_model.embed_query(text)

	def retrieve(
		self,
		query: str,
		top_k: int = 5,
		min_score: float = 0.0,
		filters: Optional[Dict[str, Any]] = None,
	) -> List[RetrievalResult]:
		raise NotImplementedError

	def retrieve_dicts(
		self,
		query: str,
		top_k: int = 5,
		min_score: float = 0.0,
		filters: Optional[Dict[str, Any]] = None,
	) -> List[Dict[str, Any]]:
		return [
			result.to_dict()
			for result in self.retrieve(query=query, top_k=top_k, min_score=min_score, filters=filters)
		]

	def retrieve_context(
		self,
		query: str,
		top_k: int = 5,
		min_score: float = 0.0,
		filters: Optional[Dict[str, Any]] = None,
	) -> str:
		results = self.retrieve(query=query, top_k=top_k, min_score=min_score, filters=filters)
		if not results:
			return ""

		sections: List[str] = []
		for idx, result in enumerate(results, start=1):
			sections.append(
				f"[{idx}] score={result.score:.4f} doc={result.doc_id} chunk={result.chunk_index}\n{result.text}"
			)
		return "\n\n".join(sections)

	def as_note_tool(self, name: str = "kb_retriever_tool") -> Callable[..., str]:
		def _tool_fn(query: str, top_k: int = 5) -> str:
			"""Tra cứu các đoạn liên quan nhất từ kho tri thức theo câu hỏi người dùng."""
			return self.retrieve_context(query=query, top_k=top_k)

		_tool_fn.__name__ = name
		if langchain_tool is not None:
			return langchain_tool(name)(_tool_fn)
		return _tool_fn


class JsonEmbeddingRetriever(BaseEmbeddingRetriever):
	def __init__(self, embeddings_path: Optional[str | Path] = None, embedding_model: Any = None) -> None:
		super().__init__(embedding_model=embedding_model)
		self.embeddings_path = Path(embeddings_path) if embeddings_path else DEFAULT_EMBEDDINGS_PATH
		self.records = self._load_embeddings(self.embeddings_path)

	@staticmethod
	def _load_embeddings(path: Path) -> List[Dict[str, Any]]:
		if not path.exists():
			raise FileNotFoundError(f"Embeddings file not found: {path}. Run kb/build_kb.py first.")
		with path.open("r", encoding="utf-8") as file:
			data = json.load(file)
		if not isinstance(data, list):
			raise ValueError("Embeddings JSON must be a list of records.")

		valid_records = [item for item in data if isinstance(item, dict) and "embedding" in item and "text" in item]
		if not valid_records:
			raise ValueError("No valid embedding records found in JSON file.")
		return valid_records

	@staticmethod
	def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
		if len(vec_a) != len(vec_b) or not vec_a:
			return 0.0
		dot = sum(a * b for a, b in zip(vec_a, vec_b))
		norm_a = math.sqrt(sum(a * a for a in vec_a))
		norm_b = math.sqrt(sum(b * b for b in vec_b))
		denominator = norm_a * norm_b
		return (dot / denominator) if denominator else 0.0

	@staticmethod
	def _match_filters(metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
		if not filters:
			return True
		for key, expected in filters.items():
			if metadata.get(key) != expected:
				return False
		return True

	def retrieve(
		self,
		query: str,
		top_k: int = 5,
		min_score: float = 0.0,
		filters: Optional[Dict[str, Any]] = None,
	) -> List[RetrievalResult]:
		query_vector = self._embed_query(query)
		scored: List[RetrievalResult] = []

		for record in self.records:
			embedding = record.get("embedding")
			if not isinstance(embedding, list):
				continue
			metadata = record.get("metadata", {}) if isinstance(record.get("metadata", {}), dict) else {}
			if not self._match_filters(metadata, filters):
				continue

			score = self._cosine_similarity(query_vector, embedding)
			if score < min_score:
				continue

			scored.append(
				RetrievalResult(
					doc_id=str(record.get("doc_id", "")),
					chunk_id=str(record.get("chunk_id", "")),
					chunk_index=int(record.get("chunk_index", 0)),
					text=str(record.get("text", "")),
					score=float(score),
					metadata=metadata,
				)
			)

		scored.sort(key=lambda item: item.score, reverse=True)
		return scored[: max(1, top_k)]


class PostgresEmbeddingRetriever(BaseEmbeddingRetriever):
	def __init__(self, embedding_model: Any = None) -> None:
		if not settings.POSTGRES_URL:
			raise ValueError("POSTGRES_URL is required for PostgreSQL retriever.")
		if psycopg2 is None:
			raise ImportError("psycopg2-binary is required for PostgreSQL retriever.")

		super().__init__(embedding_model=embedding_model)
		self.postgres_url = settings.POSTGRES_URL
		self.table_name = settings.KB_VECTOR_TABLE

	@staticmethod
	def _to_vector_literal(vector: List[float]) -> str:
		return "[" + ",".join(str(float(value)) for value in vector) + "]"

	def retrieve(
		self,
		query: str,
		top_k: int = 5,
		min_score: float = 0.0,
		filters: Optional[Dict[str, Any]] = None,
	) -> List[RetrievalResult]:
		query_vector = self._embed_query(query)
		vector_literal = self._to_vector_literal(query_vector)

		where_clauses = ["1=1"]
		params: List[Any] = [vector_literal]

		if filters:
			for key, value in filters.items():
				where_clauses.append("metadata ->> %s = %s")
				params.extend([key, str(value)])

		where_sql = " AND ".join(where_clauses)
		sql_query = f"""
			SELECT
				doc_id,
				chunk_id,
				chunk_index,
				content,
				metadata,
				1 - (embedding <=> %s::vector) AS score
			FROM {self.table_name}
			WHERE {where_sql}
			ORDER BY embedding <=> %s::vector
			LIMIT %s;
		"""

		params.append(vector_literal)
		params.append(max(1, top_k))

		results: List[RetrievalResult] = []
		with psycopg2.connect(self.postgres_url) as connection:
			with connection.cursor() as cursor:
				cursor.execute(sql_query, params)
				for row in cursor.fetchall():
					score = float(row[5])
					if score < min_score:
						continue
					metadata = row[4] if isinstance(row[4], dict) else {}
					results.append(
						RetrievalResult(
							doc_id=str(row[0]),
							chunk_id=str(row[1]),
							chunk_index=int(row[2]),
							text=str(row[3]),
							score=score,
							metadata=metadata,
						)
					)
		return results


def create_retriever(
	embeddings_path: Optional[str | Path] = None,
	embedding_model: Any = None,
	backend: Optional[str] = None,
) -> BaseEmbeddingRetriever:
	selected_backend = (backend or settings.KB_RETRIEVER_BACKEND or "postgres").lower().strip()

	if selected_backend == "postgres":
		return PostgresEmbeddingRetriever(embedding_model=embedding_model)
	return JsonEmbeddingRetriever(embeddings_path=embeddings_path, embedding_model=embedding_model)


def create_langgraph_retriever_tool(
	embeddings_path: Optional[str | Path] = None,
	name: str = "kb_retriever_tool",
	backend: Optional[str] = None,
) -> Callable[..., str]:
	retriever = create_retriever(embeddings_path=embeddings_path, backend=backend)
	return retriever.as_note_tool(name=name)
