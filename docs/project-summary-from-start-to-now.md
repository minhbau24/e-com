# Detailed Project Summary - Bookstore Microservice

Ngay cap nhat: 2026-04-02

## 1) Executive summary

Project da duoc nang cap tu mot bo microservice co cac flow co ban thanh mot he thong e-commerce co recommendation AI hoat dong end-to-end tren Docker.

Gia tri chinh da dat duoc:

- Hoan thanh luong mua hang chinh: customer -> cart -> order -> payment + shipment.
- Dong bo ton kho theo order.
- Hoan thanh review/rating cho san pham.
- Trien khai recommendation theo san pham tuong tu tren Product Detail page.
- Chuyen recommendation sang huong precompute embedding + query cosine trong DB de truy van nhanh hon.
- On dinh startup va seeding de he thong co the khoi tao lai sau reset/restart.

## 2) Kien truc tong the

He thong gom 4 lop:

1. Client layer:
- Storefront (React, phuc vu qua Nginx, port host 3000).

2. Entry layer:
- API Gateway (port host 8000), lam diem vao chinh cho frontend va test API.

3. Domain service layer:
- customer-service, staff-service, manager-service
- book-service, catalog-service
- cart-service, order-service
- pay-service, ship-service
- comment-rate-service
- recommender-ai-service

4. Data layer:
- Moi service nghiep vu su dung DB rieng (phan lon la MySQL).
- Recommender su dung PostgreSQL + pgvector.
- Data seeder khoi tao du lieu va trigger recommendation refresh.

## 3) Danh sach service va vai tro

### Frontend + gateway

- storefront (3000 -> 80): giao dien nguoi dung, route API qua gateway.
- api-gateway (8000): proxy/aggregate request den cac service backend, bao gom recommendation flow.

### Nghiep vu chinh

- customer-service (8001): quan ly khach hang, tao customer.
- cart-service (8003): gio hang va cart item.
- book-service (8002): thong tin sach, validate sach/ton kho.
- order-service (8004): tao don, dieu phoi thanh toan + van chuyen, cap nhat ton kho.
- pay-service (8005): xu ly ban ghi thanh toan.
- ship-service (8006): xu ly ban ghi giao hang.
- comment-rate-service (8007): danh gia va binh luan.
- catalog-service (8008): duyet danh muc.

### Quan tri

- staff-service (8009): thao tac staff lien quan den sach.
- manager-service (8010): thong tin manager.

### Recommendation

- recommender-ai-service (8011): build embedding va truy van san pham tuong tu.

### Khoi tao du lieu

- data-seeder: import du lieu ban dau va goi refresh embedding.

## 4) Luong nghiep vu da hoan thanh

### Flow A: Tao customer va cart

- Khi tao customer, service customer goi sang cart-service de tao cart mac dinh.
- Muc tieu dat duoc: customer moi co san gio hang ngay tu dau.

### Flow B: Them item vao cart

- cart-service validate book thong qua book-service truoc khi ghi cart item.
- Dam bao khong them item khong hop le.

### Flow C: Tao order

- order-service nhan request tao order.
- Lay du lieu cart va item.
- Goi pay-service de tao payment.
- Goi ship-service de tao shipment.
- Cap nhat/tru ton kho sach khi order thanh cong.

### Flow D: Review/rating

- comment-rate-service cho phep tao review va truy van review theo book.

## 5) Recommendation AI: tien trinh nang cap

## Giai doan 1: recommendation co ban

- Ban dau recommendation theo huong don gian.

## Giai doan 2: CLIP embedding

- Dua vao CLIP model: openai/clip-vit-base-patch32.
- Tao embedding tu text + image.
- Ket hop vector va normalize.

## Giai doan 3: DB-backed retrieval

- Chuyen tu tinh toan dong bo moi request sang precompute embedding.
- Luu embedding vao bang DB truoc.
- Luc query recommendation chi truy van cosine tren vector da luu.

## Giai doan 4: pgvector

- Chuyen recommender DB sang PostgreSQL.
- Them vector field va su dung pgvector cho cosine search.
- Co fallback path bang numpy khi can.

## Giai doan 5: API hoan chinh

- POST /recommend/refresh/: build/refresh embedding.
- GET /recommend/similar/<product_id>/: lay top-k san pham tuong tu.

Ket qua: recommendation response nhanh hon sau khi da co embedding trong DB.

## 6) Frontend integration da hoan thanh

Tren Product Detail page da them block "San pham tuong tu" voi:

- Top 5 san pham.
- Loading state.
- Error state.
- Empty state.
- Card UI va hanh dong them vao gio.

Ngoai ra da fix route proxy /recommend/ trong Nginx storefront de request tu browser di dung qua gateway.

## 7) Docker va startup orchestration

## Topology DB

- Cac service nghiep vu dung MySQL rieng.
- Recommender dung pgvector/pg16 image.

## Healthcheck va depends_on

- Co healthcheck cho MySQL va PostgreSQL.
- Book/Catalog co them healthcheck HTTP endpoint.
- Data-seeder doi cac service quan trong san sang truoc khi chay.

## Chuoi startup recommender

Da chinh startup theo huong:

1. Wait DB
2. Apply migration
3. Refresh embedding
4. Start gunicorn

Muc tieu: tranh tinh trang app chay nhung recommendation chua san sang.

## 8) Seeder va khoi tao du lieu

Seeder da duoc nang cap de:

- Import du lieu sach/catalog ban dau.
- Ghi log ro qua trinh seed.
- Goi refresh recommendation sau seed.
- Ghi log moc hoan tat (seed xong, refresh xong, init xong).

Fix gan nhat:

- Sua endpoint readiness recommender trong seeder cho dung flow recommendation moi.
- Tang timeout cho readiness len 600s de chiu duoc cold-start khi build embedding lan dau.

## 9) Cac van de da gap va da xu ly

## Nhom 1: Timeout va do ben

- Recommender/gateway timeout khi embedding lan dau qua nang.
	- Da tang timeout phu hop cho startup va API path lien quan.
- Storefront timeout 10s khi goi recommendation.
	- Da tang timeout request recommendation ben frontend.
- Seeder timeout khi doi recommender.
	- Da sua readiness URL + timeout.

## Nhom 2: Routing/proxy

- Storefront Nginx thieu proxy /recommend/.
	- Da bo sung route proxy den gateway.

## Nhom 3: DB/migration

- Migration drift/sai khac schema trong recommender.
	- Da dieu chinh migration chain.
- PostgreSQL image khong co pgvector.
	- Da chuyen sang image pgvector/pgvector:pg16.

## Nhom 4: Dependency ML

- Cai nham torch CUDA stack.
	- Da chot torch CPU wheel.
- Risk khong tuong thich numpy/torch tren Docker.
	- Da pin lai dependency theo huong on dinh cho runtime CPU.

## 10) Trang thai hien tai

Tinh den hien tai, project da dat muc:

- End-to-end bookstore microservice hoat dong tren Docker.
- Co recommendation AI tren Product Detail page.
- Co precompute embedding va vector search trong DB.
- Co startup va seeding flow cho lan khoi tao moi.

Noi ngan gon: tu mot demo microservice co ban, he thong da duoc day len muc co recommendation pipeline va kha nang khoi tao lai on dinh de demo/lab/bao cao.

## 11) Checklist demo de bao cao

1. docker compose up --build.
2. Xac nhan data-seeder chay xong va log completion.
3. Kiem tra book va catalog da co du lieu.
4. Goi gateway endpoint recommendation similar voi mot product_id ton tai.
5. Mo Product Detail tren storefront va xac nhan top-5 similar products.
6. Restart stack, lap lai buoc 4-5 de chung minh startup flow ben.

## 12) Huong phat trien tiep theo

De nang chat luong he thong, co the lam tiep:

- Tach readiness va liveness endpoint cho recommender.
- Dua refresh embedding vao background worker/scheduler thay vi trigger block startup.
- Them integration test cho flow seed -> refresh -> query recommend -> render UI.
- Them metrics (latency refresh, latency recommend, timeout count).
- Can nhac cache layer cho similar query nhieu truy cap.

---

Tai lieu nay la ban summary chi tiet nhat tinh den thoi diem cap nhat o tren, phuc vu cho demo, bao cao va handover ky thuat.
