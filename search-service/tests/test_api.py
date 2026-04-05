from fastapi.testclient import TestClient

from api.search import service
from main import app
from models.search import SearchFilters, SearchPagination, SearchProduct, SearchRequest, SearchResponse, SearchSort


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint_returns_llm_payload(monkeypatch):
    fake_response = SearchResponse(
        query="sách kiến trúc",
        filters=SearchFilters(price_min=100000),
        sort=SearchSort(field="rating", order="desc"),
        pagination=SearchPagination(page=1, size=10, total=1, total_pages=1),
        total=1,
        items=[
            SearchProduct(
                product_id="p1",
                name="Architecture Basics",
                price=150000,
                rating=4.8,
                review_count=42,
                stock=7,
                category="Books",
                author="Claudia Martinez Alonso",
                publisher="Koenemann",
                publication_year=2018,
                language="Tiếng Anh",
                cover_type="Bìa cứng",
                page_count=320,
                relevance_score=123.4,
            )
        ],
        llm_context="Query: sách kiến trúc\nTotal matches: 1",
    )

    def fake_search(payload: SearchRequest):
        return fake_response

    monkeypatch.setattr(service, "search", fake_search)

    response = client.post(
        "/search",
        json={
            "query": "sách kiến trúc",
            "filters": {"price_min": 100000},
            "sort": {"field": "rating", "order": "desc"},
            "pagination": {"page": 1, "size": 10},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "sách kiến trúc"
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Architecture Basics"
    assert body["llm_context"].startswith("Query: sách kiến trúc")
