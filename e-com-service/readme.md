# E-com Service

FastAPI service chịu trách nhiệm orchestration hội thoại cho chatbot e-commerce.

## Service này làm gì?

- Nhận request chat từ client (`/chat`).
- Phân loại intent (`rag`, `db`, `combine`) bằng LangGraph.
- Với intent `rag`: truy vấn KB/pgvector để lấy ngữ cảnh tri thức.
- Với intent `db`: gọi `search-service` để lấy dữ liệu sản phẩm thời gian thực.
- Với intent `combine`: kết hợp ngữ cảnh KB + DB trước khi sinh câu trả lời.
- Sinh câu trả lời cuối cùng bằng Gemini.

## API chính

- `POST /chat`
- `GET /health`

Ví dụ body `/chat`:

```json
{
  "user_id": "u1",
  "query": "Gợi ý sách kiến trúc cho người mới",
  "debug": true
}
```

## Biến môi trường quan trọng

- `GOOGLE_API_KEY`
- `POSTGRES_URL` (KB pgvector)
- `KB_RETRIEVER_BACKEND` (`postgres` hoặc `json`)
- `SEARCH_SERVICE_URL` (mặc định gọi sang `search-service`)

Tham khảo mẫu tại `.env.example`.

## Chạy service (khuyên dùng)

Chạy toàn bộ stack từ thư mục gốc bằng file compose duy nhất:

```bash
docker compose up -d --build
```

Service này sẽ lắng nghe tại `http://localhost:8000`.

## Chạy riêng bằng local Python

Từ thư mục `e-com-service`:

```bash
uvicorn main:app --reload --port 8000
```

Lưu ý: vẫn cần `search-service` và các PostgreSQL tương ứng đang chạy.

---

> Đây là base để bạn triển khai full system production hoặc đồ án.


---

## 12. Project Structure (Chi tiết)

```
app/
├── main.py                 # Entry point FastAPI
├── config.py               # Config (API keys, env)
│
├── api/                    # Layer expose API
│   ├── chat.py             # /chat endpoint
│   ├── recommend.py        # /recommend endpoint
│   └── track.py            # /track hành vi user
│
├── services/               # Business logic
│   ├── rag_service.py      # RAG pipeline
│   ├── db_service.py       # Query DB (price, stock)
│   ├── behavior_service.py # Gọi model_behavior
│   ├── intent_service.py   # Detect intent
│   └── combine_service.py  # Combine KB + DB
│
├── models/                 # ML models
│   └── model_behavior.py
│
├── kb/                     # Knowledge Base
│   ├── build_kb.py         # Script build KB
│   ├── documents.json      # Raw documents
│   ├── embeddings/         # Vector store
│   └── retriever.py        # Search logic
│
├── db/                     # Database layer
│   ├── connection.py
│   └── queries.py
│
├── graph/                  # LangGraph chatbot
│   ├── graph.py            # Define graph
│   └── nodes.py            # Các node (RAG, DB...)
│
└── utils/
    ├── logger.py
    └── helpers.py
```

---

## 13. Step-by-Step Implementation

### 🚀 Phase 1: Setup cơ bản

- Setup FastAPI project
- Tạo các API:
  - `/chat`
  - `/recommend`
  - `/track`
- Kết nối database (PostgreSQL / MongoDB)

---

### 🤖 Phase 2: Build Database + Query

- Thiết kế schema product
- Viết query:
  - get product
  - get stock
  - get price
- Test API DB

---

### 🧠 Phase 3: Build model_behavior

- Thu thập dữ liệu hành vi
- Feature engineering
- Train model
- Export model
- Wrap thành service

---

### 📚 Phase 4: Build Knowledge Base

- Convert product → text
- Chunk dữ liệu
- Generate embedding
- Lưu vector DB
- Test semantic search

---

### 🔍 Phase 5: Implement RAG

- Nhận query
- Embed query
- Search KB
- Gọi Google LLM API
- Trả kết quả

---

### 🔀 Phase 6: Intent Detection

- Rule-based (ban đầu)
- Sau đó nâng cấp bằng LLM

---

### 🔗 Phase 7: Hybrid (KB + DB)

- Nếu advice → RAG
- Nếu stock/price → DB
- Nếu hybrid → combine

---

### 🧩 Phase 8: LangGraph Chatbot

- Define nodes:
  - intent
  - rag
  - db
  - combine
- Build graph flow
- Test end-to-end

---

### ⚡ Phase 9: Optimization

- Cache (Redis)
- Reduce latency
- Improve prompt
- Ranking output

---

### ☁️ Phase 10: Deployment

- Dockerize services
- Deploy (AWS/GCP)
- Setup logging & monitoring

---

## 14. Execution Flow (Final)

```
User → /chat
     → Intent Detection
     →
        ├── RAG (KB)
        ├── DB Query
        └── Combine
     → LLM (Google API)
     → Response
```

---

> Nếu bạn làm đúng theo flow này, bạn sẽ có một hệ thống e-commerce AI hoàn chỉnh (gần production-ready).

