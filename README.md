# 🧠 FiscalMind

> **Hệ thống AI SaaS Phân tích Báo cáo Tài chính Doanh nghiệp (AI-powered assistant for enterprise financial statement analysis).**

FiscalMind hoạt động như một Giám đốc Tài chính (CFO ảo) và Chuyên viên kiểm toán cấp cao. Người dùng tải lên các báo cáo tài chính (PDF/Excel) và tương tác tự nhiên với tài liệu của họ — nhận phân tích chỉ số tự động, báo cáo so sánh trung bình ngành, nhận định điểm mạnh/yếu bằng AI và dẫn nguồn trích dẫn số liệu gốc chính xác.

---

## 🏗️ Kiến trúc Kỹ thuật (Clean Architecture)

Hệ thống được thiết kế theo nguyên lý **Clean Architecture + Domain Driven Design** kết hợp với kiến trúc xử lý tác vụ ngầm bất đồng bộ:
`API Layer (FastAPI) → Services Layer → Repositories Layer → Database Layer (Supabase Cloud)`

```
[FastAPI Backend] ──► [Redis Broker] ──► [Celery Worker] ──► [PaddleOCR Local]
        │                                       │
        ▼ (Query SQL)                           ▼ (Embed / Search)
[Supabase Postgres Cloud]               [Qdrant Cloud & Voyage AI API]
```

---

## 🚀 Hướng dẫn khởi chạy nhanh (Quick Start)

### 1. Chuẩn bị môi trường
Yêu cầu máy Mac của bạn đã cài đặt:
*   Docker & Docker Compose.
*   Ứng dụng **Docker Desktop** đã được mở.

### 2. Cấu hình các biến môi trường
Sao chép file cấu hình mẫu và điền thông tin các API Keys của bạn:
```bash
cp backend/.env.example backend/.env
```

Mở file `backend/.env` và thiết lập các API Keys Cloud:
*   `DATABASE_URL`: Đường dẫn kết nối tới **Supabase Cloud** (đã cấu hình sẵn url-encode mật khẩu).
*   `VOYAGE_API_KEY`: API Key lấy từ Voyage AI Console.
*   `QDRANT_URL` & `QDRANT_API_KEY`: Địa chỉ cụm đám mây và Token lấy từ Qdrant Cloud.
*   `GROQ_API_KEY`: API Key lấy từ Groq Console (sử dụng mô hình Llama 3.3).

### 3. Khởi động toàn bộ dịch vụ
Chạy lệnh Makefile ở thư mục gốc để Docker tự động tải ảnh, dựng container và chạy Migration cơ sở dữ liệu trên Supabase:
```bash
make up
```

### 4. Kiểm tra trạng thái hệ thống
Kiểm tra xem hệ thống đã hoạt động bình thường chưa:
```bash
curl http://localhost:8000/api/v1/health
```

Tài liệu API Swagger tương tác trực tiếp:
Mở trình duyệt truy cập: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

---

## 🛠️ Công nghệ tích hợp (Tech Stack)

| Hợp phần | Công nghệ tích hợp |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python) chạy chế độ Async |
| **Cơ sở dữ liệu chính** | Supabase Cloud (PostgreSQL 16) |
| **Hệ thống di trú DB** | Alembic Migrations |
| **Hàng đợi & Lưu đệm** | Redis 7 + Celery Workers |
| **Vector DB** | Qdrant Cloud Cluster |
| **AI Models (RAG)** | Voyage AI API (`voyage-multilingual-2` & `rerank-2.5`) |
| **AI Inference (LLM)** | Groq API (`llama-3.3-70b-versatile` chạy Structured JSON Mode) |
| **OCR Engine** | PaddleOCR Local Service (OCR thô trong ảnh PDF) |

---

## 📦 Cấu trúc Thư mục Dự án

```
FiscalMind/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # Bộ điều phối API Router (Auth, Documents, Chat, Analysis, Insights, Benchmarks, Dashboard)
│   │   ├── core/           # Cấu hình hệ thống, kết nối DB, Redis, Log, Exception
│   │   ├── models/         # SQLAlchemy ORM Models (User, Document, Conversation, Message, CustomBenchmark)
│   │   ├── schemas/        # Pydantic Schemas quản lý định dạng Dữ liệu vào/ra
│   │   ├── repositories/   # Lớp truy vấn Database (Repositories Pattern)
│   │   ├── services/       # Lớp xử lý Logic nghiệp vụ chính (Services Layer)
│   │   ├── rag/            # Pipeline xử lý chunking, embedder, reranker, retriever
│   │   ├── financial_engine/ # Công thức toán, OCR client, bộ tính chỉ số, bộ phân giải ngành
│   │   └── tasks/          # Celery background tasks chạy ngầm xử lý file
│   ├── alembic/            # Thư mục lịch sử di trú Database
│   └── tests/              # Thư mục bộ unit test và integration test
├── ocr_service/            # Thư mục PaddleOCR clone cục bộ chạy trên Docker riêng
├── docker-compose.yml      # Cấu hình container chạy các microservices
└── Makefile                # Bộ phím tắt dòng lệnh phát triển nhanh
```

---

## 🔧 Các lệnh phát triển thông dụng (Developer Commands)

Sử dụng `make` để điều phối nhanh các hoạt động trên terminal:
*   `make up` : Khởi chạy toàn bộ hệ thống (dựng cả service backend, celery worker, redis, postgres và ocr).
*   `make down` : Dừng toàn bộ các dịch vụ.
*   `make logs` : Theo dõi log thời gian thực của các container.
*   `make migrate` : Chạy thủ công cập nhật database migration lên Supabase.
*   `make test` : Chạy thử nghiệm toàn bộ bộ kiểm thử trong môi trường container.
*   `make shell-backend` : Truy cập vào shell terminal bên trong container backend.

---

## 🗺️ Bản đồ các Phase phát triển (Implementation Progress)

| Phase | Trạng thái | Lĩnh vực | Chi tiết |
| :--- | :--- | :--- | :--- |
| **Phase 1** | ✅ Hoàn thành | Hạ tầng nền tảng | Thiết lập FastAPI, Docker, Redis, Celery và Alembic. |
| **Phase 2** | ✅ Hoàn thành | Xác thực | JWT Auth, băm mật khẩu, phân quyền cách ly User. |
| **Phase 3** | ✅ Hoàn thành | Tài liệu | API upload, Soft-delete, Versioning tài liệu. |
| **Phase 4** | ✅ Hoàn thành | Parser & OCR | PaddleOCR, bóc tách bảng số liệu chuẩn hóa sang JSONB. |
| **Phase 5** | ✅ Hoàn thành | RAG Pipeline | Lập chỉ mục Qdrant Cloud, Voyage embedder & reranker. |
| **Phase 6** | ✅ Hoàn thành | Trò chuyện AI | Chat SSE streaming (Llama 3.3), dẫn nguồn Citations. |
| **Phase 7** | ✅ Hoàn thành | Analysis Engine | Tự động tính toán 10 chỉ số tài chính cốt lõi an toàn. |
| **Phase 8** | ✅ Hoàn thành | Insight Engine | AI nhận định chuyên sâu Điểm mạnh/Điểm yếu dạng JSON. |
| **Phase 9** | ✅ Hoàn thành | Dashboard | API tổng hợp số liệu trang chủ trong một lượt gọi mạng. |
| **Phase 10**| ✅ Hoàn thành | So sánh chéo | Đối chiếu song song chỉ số các doanh nghiệp kèm AI chéo. |
| **Phase 11**| ✅ Hoàn thành | Benchmarking | So sánh trung bình ngành động, Strategy Pattern. |
| **Phase 12**| ⏳ Đang làm | DevOps | Tối ưu hóa Docker sản xuất, bảo mật CORS, đóng gói. |
