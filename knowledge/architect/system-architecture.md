# System Architecture

## Components

- `src/ingest.py` - đọc local knowledge files, chunk theo paragraph/sentence với heading context và overlap, embed, rồi upsert vào Qdrant.
- `src/qdrant_store.py` - tầng duy nhất giao tiếp với Qdrant (tạo collection, upsert, search, scroll, xóa theo file nguồn).
- `src/knowledge.py` - logic quản lý knowledge: liệt kê, đọc, sửa, xóa file + đồng bộ vector, dọn vector rác.
- `src/model_provider.py` - chọn OpenAI/Ollama client và model cho chat hoặc embeddings từ environment.
- `src/query.py` - retrieval, hybrid rerank và MMR, rồi gửi context tới provider chat đã chọn.
- `src/tools.py` - routing helper cho summaries, reports, text files và binary artifacts.
- `src/artifacts.py` - gọi Images API và dựng workbook XLSX thật từ JSON có cấu trúc do AI sinh.
- `src/agent.py` - simple router chọn tool cần gọi.
- `src/app.py` - Streamlit UI: trang Chat và trang Quản lý Knowledge.

## Luồng dữ liệu

```mermaid
flowchart TD
    A[Local knowledge files] --> B[Chunking]
    B --> C[OpenAI or Ollama embeddings]
    C --> D[Qdrant collection home_knowledge]
    E[User prompt in Streamlit] --> F[Semantic candidate retrieval]
    F --> I[Hybrid BM25 reranking and MMR selection]
    I --> G[OpenAI or Ollama chat model]
    G --> H[Answer rendered in UI]
```

## Storage

- Persistent vector data: Qdrant, chạy trong container riêng, dữ liệu lưu ở Docker volume `qdrant_storage`
- Environment config: `.env`
- Source knowledge: `data/knowledge/` (mount vào container app)

## Triển khai

- Cài đặt bằng Docker Compose: service `app` (Streamlit) + service `qdrant`.
- Entrypoint của app đợi Qdrant sẵn sàng rồi chạy `python src/ingest.py --if-empty` để train lần đầu khi Qdrant đang trống.
- Point ID là UUID v5 ổn định sinh từ source + chunk_index + nội dung chunk, nên ingest lại không tạo point trùng.
- Payload mỗi point gồm `source`, `chunk_index`, `content`; field `source` có payload index để xóa/đếm theo file nhanh.

## Ghi chú về behavior hiện tại

- Sidebar quick prompts chỉ prefill input field.
- Nút Send là trigger chạy assistant.
- Các lượt user/assistant gần nhất được gửi lại cho model trong cùng Streamlit session; tối đa 10 messages hoặc 12.000 ký tự.
- Clear chat xóa cả conversation context và generated artifact của session.
- Ảnh được render/tải dạng PNG; Excel được tạo dạng XLSX với header style, filter, freeze panes và column widths.
- Chat history hiển thị dưới dạng collapsed expanders.
- File-generation request đi qua generation prompt riêng, không dùng template placeholder; download MIME được chọn theo extension.

## Retrieval configuration

- `AI_PROVIDER`: provider mặc định (`openai` hoặc `ollama`).
- `CHAT_PROVIDER`, `EMBEDDING_PROVIDER`: override riêng cho từng luồng.
- Đổi embedding provider/model yêu cầu rebuild Qdrant collection (app tự xóa và tạo lại collection khi vector size khác).
- Quản lý Knowledge trong UI: sửa file -> train lại file đó; xóa file -> xóa cả vector; vector rác (file đã xóa ngoài UI) dọn bằng nút riêng.

- `RAG_TOP_K`: số chunk cuối cùng đưa vào generation, mặc định `5`.
- `RAG_CANDIDATE_K`: kích thước semantic candidate pool trước reranking, mặc định `20`.
- `RAG_MMR_LAMBDA`: cân bằng relevance/diversity trong MMR, mặc định `0.75`.
- `RAG_CHUNK_SIZE`: kích thước chunk mục tiêu theo ký tự, mặc định `1200`.
- `RAG_CHUNK_OVERLAP`: overlap giữa các chunk theo ký tự, mặc định `180`.
