from models.search import SearchFilters, SearchPagination, SearchRequest, SearchSort
import db.queries as queries
from db.queries import build_generated_search_sql, build_llm_context, build_search_sql, normalize_text
from services.search_service import _extract_total_from_count_row


def test_normalize_text_removes_accents_and_collapses_spaces():
    assert normalize_text("  Sách   Kiến  Trúc  ") == "sach kien truc"


def test_build_search_sql_with_filters_and_sort():
    request = SearchRequest(
        query="sách kiến trúc",
        filters=SearchFilters(
            price_min=100000,
            price_max=1000000,
            author="Claudia Martinez Alonso",
            publisher="Koenemann",
            publication_year_min=2010,
            publication_year_max=2020,
            language="Tiếng Anh",
            cover_type="Bìa cứng",
            page_count_min=100,
            page_count_max=600,
            in_stock=True,
        ),
        sort=SearchSort(field="rating", order="desc"),
        pagination=SearchPagination(page=2, size=10),
    )

    select_sql, count_sql, params = build_search_sql(request)

    assert "FROM search_products" in select_sql
    assert "price >= %(price_min)s" in select_sql
    assert "price <= %(price_max)s" in select_sql
    assert "author ILIKE %(author)s" in select_sql
    assert "publisher ILIKE %(publisher)s" in select_sql
    assert "publication_year >= %(publication_year_min)s" in select_sql
    assert "publication_year <= %(publication_year_max)s" in select_sql
    assert "language ILIKE %(language)s" in select_sql
    assert "cover_type ILIKE %(cover_type)s" in select_sql
    assert "page_count >= %(page_count_min)s" in select_sql
    assert "page_count <= %(page_count_max)s" in select_sql
    assert "stock > 0" in select_sql
    assert "ORDER BY rating DESC" in select_sql
    assert "COUNT(*) AS total" in count_sql
    assert params["query_like"] == "%sách kiến trúc%"
    assert params["normalized_query_like"] == "%sach kien truc%"
    assert params["limit"] == 10
    assert params["offset"] == 10
    assert params["has_query"] is True


def test_build_llm_context_includes_compact_book_summary():
    request = SearchRequest(query="kiến trúc")
    context = build_llm_context(
        [
            {
                "name": "Architecture Basics",
                "price": 150000,
                "rating": 4.8,
                "review_count": 42,
                "stock": 7,
                "category": "Books",
                "author": "Claudia Martinez Alonso",
                "publisher": "Koenemann",
                "publication_year": 2018,
                "language": "Tiếng Anh",
                "cover_type": "Bìa cứng",
                "page_count": 320,
            }
        ],
        total=1,
        request=request,
    )

    assert "Query: kiến trúc" in context
    assert "Total matches: 1" in context
    assert "Architecture Basics" in context
    assert "author=Claudia Martinez Alonso" in context
    assert "publisher=Koenemann" in context
    assert "pages=320" in context


def test_build_generated_search_sql_uses_llm_payload(monkeypatch):
    class FakeResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeLLM:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def invoke(self, messages):
            return FakeResponse(
                """
                {
                  "select_sql": "SELECT product_id, name, price, rating, review_count, stock, category, content, author, publisher, publication_year, language, cover_type, page_count, created_at, COALESCE(rating, 0) AS relevance_score FROM search_products WHERE (name ILIKE %(term_1)s OR normalized_name ILIKE %(term_1)s OR content ILIKE %(term_1)s OR category ILIKE %(term_2)s) AND stock > 0 ORDER BY relevance_score DESC, rating DESC, review_count DESC, created_at DESC LIMIT %(limit)s OFFSET %(offset)s",
                  "count_sql": "SELECT COUNT(*) AS total FROM search_products WHERE (name ILIKE %(term_1)s OR normalized_name ILIKE %(term_1)s OR content ILIKE %(term_1)s OR category ILIKE %(term_2)s) AND stock > 0",
                  "params": {
                    "term_1": "%kien truc%",
                    "term_2": "%books%"
                  }
                }
                """
            )

    monkeypatch.setattr(queries, "ChatGoogleGenerativeAI", FakeLLM)
    monkeypatch.setattr(queries, "HumanMessage", FakeMessage)
    monkeypatch.setattr(queries, "SystemMessage", FakeMessage)
    monkeypatch.setattr(queries.settings, "GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(queries.settings, "SEARCH_SQL_GENERATION_ENABLED", True)

    request = SearchRequest(query="sách kiến trúc", filters=SearchFilters(in_stock=True), pagination=SearchPagination(page=1, size=5))
    select_sql, count_sql, params = build_generated_search_sql(request)

    assert "FROM search_products" in select_sql
    assert "COUNT(*) AS total" in count_sql
    assert params["term_1"] == "%kien truc%"
    assert params["term_2"] == "%books%"
    assert params["limit"] == 5
    assert params["offset"] == 0


def test_extract_total_from_count_row_accepts_non_total_alias():
    assert _extract_total_from_count_row({"count": 7}) == 7
    assert _extract_total_from_count_row({"total": 9}) == 9
