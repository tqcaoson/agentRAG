# AgentRAG — Personal RAG Assistant (Docker + Qdrant)

Trợ lý RAG cá nhân chạy trên máy của bạn: đọc ghi chú project, ghi chú học
tập, daily note và task cá nhân, rồi trả lời câu hỏi dựa trên chính những
tài liệu đó.

**Cơ chế:** máy local làm harness (chạy app Streamlit + vector database
Qdrant trong Docker), LLM dùng **OpenAI API** cho chat, embedding và tạo
ảnh. Dữ liệu knowledge vẫn nằm trên máy bạn, dưới dạng file `.md` / `.txt` /
`.csv` trong `data/knowledge/`.

## Có gì mới so với bản cũ

| Trước đây | Bây giờ |
|---|---|
| Cài bằng `venv` + `pip` thủ công | Cài bằng Docker Compose, 1 lệnh chạy |
| ChromaDB lưu local trong `storage/chroma_db` | Qdrant chạy trong container riêng, có dashboard |
| Thêm/sửa knowledge chỉ bằng cách sửa file + chạy lệnh | Thêm trang **Quản lý Knowledge** trong UI: xem, sửa, xóa, train lại từng file |
| Hướng dẫn ngắn trong README | Có [hướng dẫn cài đặt](HUONG-DAN-CAI-DAT.md) và [hướng dẫn sử dụng + training](HUONG-DAN-SU-DUNG-VA-TRAINING.md) riêng |

Luồng RAG không đổi: chunk theo đoạn văn có giữ heading context +
overlap → embedding OpenAI → tìm ứng viên theo vector → rerank kết hợp
BM25 + MMR → OpenAI chat trả lời kèm nguồn.

## Kiến trúc

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  data/knowledge │     │  app (Streamlit) │     │  Qdrant         │
│  .md/.txt/.csv  │────▶│  - Chat / Agent  │────▶│  collection:    │
│  (file trên host│     │  - Ingest/chunk  │     │  home_knowledge │
│   mount vào app)│     │  - Quản lý KB    │     │  (Docker volume)│
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │ OpenAI API (chat + embedding + ảnh)
                                 ▼
                        ┌──────────────────┐
                        │  api.openai.com  │
                        └──────────────────┘
```

## Chạy nhanh (Docker — cách khuyên dùng)

Yêu cầu: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(Windows/Mac) hoặc Docker Engine + Docker Compose (Linux), và 1 OpenAI API key.

```bash
# 1. Vào thư mục project
cd agentRAG-main

# 2. Tạo file cấu hình, điền OPENAI_API_KEY
cp .env.example .env

# 3. Chạy
docker compose up -d --build

# 4. Mở trình duyệt
# App:      http://localhost:8501
# Qdrant:   http://localhost:6333/dashboard
```

Lần đầu chạy, app tự train knowledge mẫu trong `data/knowledge/` (nếu Qdrant
đang trống). Xem chi tiết từng bước, kể cả cách kiểm tra và xử lý lỗi, trong
[HUONG-DAN-CAI-DAT.md](HUONG-DAN-CAI-DAT.md).

Dừng app: `docker compose down` (dữ liệu Qdrant vẫn giữ trong volume).
Dừng và xóa cả dữ liệu vector: `docker compose down -v`.

## Chạy không cần Docker (tùy chọn)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # điền OPENAI_API_KEY
```

Cần 1 Qdrant đang chạy ở `QDRANT_URL` (mặc định `http://localhost:6333`),
ví dụ chạy riêng bằng Docker:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:v1.11.3
```

Rồi train và chạy app:

```bash
python src/ingest.py
python -m streamlit run src/app.py
```

## Cấu hình (.env)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | _(bắt buộc)_ | Key OpenAI, lấy tại platform.openai.com/api-keys |
| `AI_PROVIDER` | `openai` | Provider mặc định cho chat + embedding |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Model trả lời |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model embedding (1536 chiều) |
| `QDRANT_URL` | `http://localhost:6333` | Địa chỉ Qdrant (trong Compose app tự dùng `http://qdrant:6333`) |
| `QDRANT_COLLECTION` | `home_knowledge` | Tên collection trong Qdrant |
| `QDRANT_API_KEY` | _(trống)_ | Chỉ cần nếu Qdrant của bạn bật auth |
| `AUTO_INGEST_ON_START` | `true` | Tự train knowledge khi container khởi động mà Qdrant đang trống |
| `RAG_ENABLED` | `true` | `false` = chat trực tiếp, bỏ qua retrieval |
| `RAG_TOP_K` | `5` | Số chunk cuối cùng đưa vào câu trả lời |
| `RAG_CANDIDATE_K` | `20` | Số ứng viên vector trước khi rerank |
| `RAG_MMR_LAMBDA` | `0.75` | Cân bằng liên quan / đa dạng khi chọn chunk |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | `1200` / `180` | Kích thước chunk và độ chồng lấn (ký tự) |

Đổi provider chat/embedding riêng lẻ bằng `CHAT_PROVIDER` /
`EMBEDDING_PROVIDER` (`openai` hoặc `ollama`). Ollama vẫn được giữ lại
làm lựa chọn thay thế, nhưng mặc định và hướng dẫn chính dùng OpenAI.

## Sử dụng

- **Chat:** hỏi về project, note, task của bạn. App nhớ tối đa 10 lượt
  gần nhất trong phiên. Nút Clear chat xóa context.
- **Tạo file:** `tạo file story.txt kể một câu chuyện...` → sinh nội dung
  thật và hiện nút tải file đúng định dạng (`.txt/.md/.csv/.json/.html`).
- **Tạo ảnh:** `tạo ảnh robot trong vườn` → ảnh PNG, xem trước và tải về.
- **Tạo Excel:** `tạo file plan.xlsx gồm kế hoạch 7 ngày` → workbook thật.
- **Quản lý Knowledge:** chọn **📚 Quản lý Knowledge** ở sidebar để xem
  danh sách tài liệu đã train, sửa nội dung (lưu là train lại ngay), xóa
  file (xóa cả vector), xem/xóa từng chunk, dọn vector rác, train lại
  toàn bộ. Chi tiết trong [HUONG-DAN-SU-DUNG-VA-TRAINING.md](HUONG-DAN-SU-DUNG-VA-TRAINING.md).

## Training (nạp knowledge)

1. Thêm file `.md` / `.txt` / `.csv` vào `data/knowledge/` (các thư mục
   `00_personal_project`, `01_learning`, `02_notes`, `03_tasks`, hoặc
   thư mục mới tùy ý), hoặc upload trực tiếp trong UI.
2. Train lại — 1 trong 2 cách:
   - Trong UI: trang Quản lý Knowledge → **Train lại toàn bộ** (hoặc
     **Train lại** ở từng file).
   - Bằng lệnh: `docker compose exec app python src/ingest.py`
3. Hỏi thử trong khung chat để kiểm tra.

Khi đổi embedding model/provider, **bắt buộc** train lại toàn bộ vì
kích thước vector thay đổi (app tự xóa và tạo lại collection).

## Cấu trúc thư mục

```
agentRAG-main/
├── docker-compose.yml      # 2 service: app + qdrant
├── Dockerfile              # image cho app Streamlit
├── docker-entrypoint.sh    # đợi Qdrant, ingest lần đầu, chạy Streamlit
├── .env.example            # mẫu cấu hình
├── requirements.txt
├── HUONG-DAN-CAI-DAT.md
├── HUONG-DAN-SU-DUNG-VA-TRAINING.md
├── data/knowledge/         # knowledge gốc (file .md/.txt/.csv)
├── src/
│   ├── app.py              # Streamlit UI: Chat + Quản lý Knowledge
│   ├── agent.py            # router chọn tool theo yêu cầu
│   ├── ingest.py           # chunk + embed + upsert vào Qdrant
│   ├── qdrant_store.py     # mọi thao tác với Qdrant (tầng duy nhất)
│   ├── query.py            # retrieval (vector + BM25 + MMR) + chat
│   ├── knowledge.py        # logic quản lý knowledge (sửa/xóa/train lại)
│   ├── model_provider.py   # chọn client OpenAI/Ollama
│   ├── tools.py            # tóm tắt task, plan, report, tạo file
│   └── artifacts.py        # tạo ảnh PNG và workbook XLSX
├── knowledge/              # tài liệu nội bộ của project (Copilot pack)
└── storage/knowledge_index.json   # snapshot tham khảo (không dùng runtime)
```

## Chuyển từ bản ChromaDB cũ

Không cần migrate dữ liệu vector: file trong `data/knowledge/` là nguồn
sự thật, chỉ cần train lại là Qdrant có đủ dữ liệu. Sau khi train xong
và kiểm tra chat trả lời đúng, có thể xóa thư mục `storage/chroma_db`
cũ để giải phóng dung lượng. Các biến `CHROMA_PATH` / `CHROMA_COLLECTION`
trong `.env` cũ không còn tác dụng, thay bằng `QDRANT_URL` /
`QDRANT_COLLECTION`.

## Copilot knowledge pack

- Project memory và Copilot guidance nằm trong [knowledge/README.md](knowledge/README.md)
  và [.github/copilot-instructions.md](.github/copilot-instructions.md).
- Hãy giữ các tài liệu này đồng bộ với thay đổi ở RAG flow, UI behavior,
  hoặc startup commands.
