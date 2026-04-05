# E-com Microservices Workspace

Workspace này gồm 2 service chính:

- `e-com-service`: chatbot orchestration (intent, RAG, DB, output).
- `search-service`: tìm kiếm sản phẩm có cấu trúc, trả dữ liệu + `llm_context`.

Toàn bộ container hiện chạy bằng **một file duy nhất** tại thư mục gốc: `docker-compose.yml`.

## Kiến trúc nhanh

- `kb-postgres` (port `5432`): pgvector cho KB của `e-com-service`.
- `search-postgres` (port `5433`): Postgres cho `search-service`.
- `search-api` (port `8001`): API tìm kiếm.
- `ecom-api` (port `8000`): API chatbot.
- `seed-search` (profile `seed`): import catalog vào `search_products`.
- `seed-kb` (profile `seed`): build KB embeddings (khi có `GOOGLE_API_KEY`).

## Chuẩn bị môi trường

1. Tạo file env cho từng service:

```bash
cp e-com-service/.env.example e-com-service/.env
cp search-service/.env.example search-service/.env
```

2. Điền các biến cần thiết, đặc biệt:

- `e-com-service/.env`: `GOOGLE_API_KEY`, `POSTGRES_URL`, `SEARCH_SERVICE_URL`
- `search-service/.env`: `POSTGRES_URL`, `GOOGLE_API_KEY` (nếu bật SQL generation)

## Chạy toàn bộ hệ thống

```bash
docker compose up -d --build
```

Health check:

- `http://localhost:8000/health`
- `http://localhost:8001/health`

## Seed dữ liệu (tuỳ chọn)

Import dữ liệu search:

```bash
docker compose --profile seed run --rm seed-search
```

Build KB embeddings:

```bash
docker compose --profile seed run --rm seed-kb
```

## Chạy test nhanh

```bash
pytest search-service/tests/test_queries.py search-service/tests/test_api.py
```

## API chính

### Chatbot API (`e-com-service`)

- `POST /chat`
- base URL: `http://localhost:8000`

Ví dụ body:

```json
{
  "user_id": "u1",
  "query": "Cho tôi sách của tác giả Claudia Martinez Alonso",
  "debug": true
}
```

### Search API (`search-service`)

- `POST /search`
- base URL: `http://localhost:8001`

Ví dụ body:

```json
{
  "query": "sách kiến trúc",
  "filters": {
    "author": "Claudia Martinez Alonso",
    "in_stock": true
  },
  "sort": {
    "field": "relevance",
    "order": "desc"
  },
  "pagination": {
    "page": 1,
    "size": 5
  }
}
```
