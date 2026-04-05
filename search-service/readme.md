# Search Service

FastAPI service chuyên trách tìm kiếm sản phẩm có cấu trúc cho chatbot và các service downstream.

## Service này làm gì?

- Nhận payload tìm kiếm dạng `query + filters + sort + pagination`.
- Sinh SQL an toàn (LLM generation có kiểm soát + fallback deterministic).
- Truy vấn bảng `search_products`.
- Trả về:
  - `items` (dữ liệu sản phẩm có cấu trúc)
  - `total`, `pagination`
  - `llm_context` (chuỗi tóm tắt để feed vào LLM của service khác)

## API chính

- `POST /search`
- `GET /health`

Ví dụ request:

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

## Biến môi trường quan trọng

- `POSTGRES_URL`
- `SEARCH_PRODUCTS_TABLE`
- `GOOGLE_API_KEY`
- `SEARCH_SQL_GENERATION_ENABLED`
- `SEARCH_SQL_MODEL`

Tham khảo mẫu tại `.env.example`.

## Chạy service (khuyên dùng)

Chạy toàn bộ stack từ thư mục gốc bằng compose duy nhất:

```bash
docker compose up -d --build
```

Service này sẽ lắng nghe tại `http://localhost:8001`.

## Chạy riêng bằng local Python

Từ thư mục `search-service`:

```bash
uvicorn main:app --reload --port 8001
```

## Nạp dữ liệu catalog vào `search_products`

Từ thư mục `search-service`:

```bash
python scripts/import_products.py --database-url "$env:POSTGRES_URL"
```

Hoặc chỉ định source/table:

```bash
python scripts/import_products.py --source "../e-com-service/data/product.csv" --table search_products
```
