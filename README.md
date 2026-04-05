# Bookstore Microservice Workspace

## 1. Mo ta so luoc du an

Day la he thong Bookstore theo mo hinh microservices, trong do:

- `api-gateway` la diem vao duy nhat cho frontend va script test.
- Cac service nghiep vu chinh: `book-service`, `cart-service`, `order-service`, `customer-service`, `comment-rate-service`, ...
- `e-com-service` xu ly chatbot/retrieval.
- `search-service` xu ly tim kiem san pham.
- `storefront` la frontend (Vite build + Nginx trong Docker).
- He thong dung 2 DB:
  - MySQL cho cac service Django nghiep vu.
  - PostgreSQL (pgvector) cho e-com/search.

Muc tieu chinh: mo phong luong mua hang va chatbot trong mot he thong e-commerce da tach service.

## 2. Cach chay tu dau den cuoi

### 2.1. Yeu cau moi truong

- Docker Desktop (co Docker Compose v2).
- Port trong may khong bi trung: `80`, `8000`, `8001`, `8002`, `3307`, `5432`.

### 2.2. Chuan bi file env

Tao file env tu template:

```bash
copy e-com-service\.env.example e-com-service\.env
copy search-service\.env.example search-service\.env
```

Neu ban dung PowerShell:

```powershell
Copy-Item e-com-service/.env.example e-com-service/.env
Copy-Item search-service/.env.example search-service/.env
```

Luu y quan trong:

- `POSTGRES_URL` phai duoc set dung cho `e-com-service` va `search-service`.
- Neu can tinh nang LLM day du, bo sung `GOOGLE_API_KEY` vao env cua `e-com-service`.

### 2.3. Build va start toan bo stack

Chay tu root workspace:

```bash
docker compose build base-image
docker compose up -d --build
```

Neu gap loi metadata voi `bookstore-base:latest`, build lai base khong dung cache:

```bash
docker compose build --no-cache base-image
docker compose up -d --build
```

Kiem tra nhanh:

- Gateway: `http://localhost:8000/`
- Search API health: `http://localhost:8001/health`
- E-com API health (direct): `http://localhost:8002/health`
- Frontend: `http://localhost/`


## 3. Cach sinh du lieu mau

Script all-in-one:

```bash
python scripts/run_sync_seed_and_simulate.py --source product.csv --product 0
```

Script nay se:

- Seed du lieu search/KB theo cung 1 nguon CSV.
- Chay mo phong tao customer, them cart item, tao order qua `api-gateway`.

Chi can chay tu thu muc goc project sau khi stack da len (`docker compose up -d --build`).

#### Cac lenh thuong dung cho file `run_sync_seed_and_simulate.py`

- Chay day du (seed + simulate):

```bash
python scripts/run_sync_seed_and_simulate.py
```

- Chay day du voi file CSV va so luong product cu the:

```bash
python scripts/run_sync_seed_and_simulate.py --source product.csv --products 20
```

- Chi seed du lieu (khong simulate):

```bash
python scripts/run_sync_seed_and_simulate.py --seed-only
```

- Chi simulate (bo qua seed):

```bash
python scripts/run_sync_seed_and_simulate.py --simulate-only
```

- Skip buoc KB neu chua co `GOOGLE_API_KEY`:

```bash
python scripts/run_sync_seed_and_simulate.py --skip-if-no-google-key
```

- Cau hinh mo phong nhieu user/order hon:

```bash
python scripts/run_sync_seed_and_simulate.py --users 10 --orders-per-user 3 --min-items 1 --max-items 4
```

- Doi gateway hoac database-url (neu can):

```bash
python scripts/run_sync_seed_and_simulate.py --gateway http://localhost:8000 --database-url postgresql://ecom_user:ecom_password@localhost:5432/ecom_db
```

Mot so option huu ich:

```bash
python scripts/run_sync_seed_and_simulate.py --seed-only
python scripts/run_sync_seed_and_simulate.py --simulate-only
python scripts/run_sync_seed_and_simulate.py --users 10 --orders-per-user 3
```

## 4. Lenh don dep/co ban

- Dung he thong:

```bash
docker compose down
```

- Dung va xoa volume (reset DB):

```bash
docker compose down -v
```

- Xem log mot service:

```bash
docker compose logs -f api-gateway
docker compose logs -f ecom-api
docker compose logs -f search-api
```

## 5. Ghi chu

- Frontend da duoc cau hinh goi gateway qua `http://localhost:8000`.
- Chat endpoint qua gateway dung duong dan: `POST /chat/`.
