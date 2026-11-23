# Project Memory

## Durable facts

- Local vector storage là Qdrant (collection `home_knowledge`), chạy trong Docker, dữ liệu ở volume `qdrant_storage`. ChromaDB đã bị thay thế hoàn toàn.
- Cài đặt/chạy bằng Docker Compose (`docker compose up -d --build`); app tự train lần đầu khi Qdrant trống.
- Provider mặc định là OpenAI; có thể chuyển chat và embeddings sang Ollama bằng `.env`.
- OpenAI defaults: chat `gpt-4o-mini`, embedding `text-embedding-3-small`.
- Ollama defaults: chat `llama3.2`, embedding `nomic-embed-text`.
- Streamlit là UI layer.
- OpenAI image model default: `gpt-image-1`.
- Image quality default: `auto`; không gửi `response_format` vì endpoint hiện tại trả base64 mặc định và từ chối tham số này.

## Known decisions

- Giữ assistant local-first cho retrieval.
- Chat và embeddings hỗ trợ OpenAI/Ollama và cấu hình hybrid.
- Giữ UI đơn giản và dễ debug.
- Sidebar quick prompts chỉ nên prefill prompt input.
- Nút Send phải execute assistant.
- History nên ở trạng thái collapsed cho tới khi mở ra.
- Retrieval dùng semantic candidate search, BM25 lexical reranking và MMR diversity selection.
- Chunking giữ heading context, ưu tiên sentence boundary và có overlap để tránh mất ngữ cảnh ở biên.
- Yêu cầu tạo file phải sinh nội dung hoàn chỉnh bằng OpenAI theo extension; không trả placeholder hoặc chỉ lặp lại prompt.
- Chat memory chỉ tồn tại trong Streamlit session và dùng bounded history để kiểm soát token.
- Image generation trả PNG binary; Excel generation trả workbook XLSX thật, không phải text đổi extension.

## Operational notes

- Rebuild vector database sau khi thay đổi source knowledge.
- OpenAI flow phải fail loudly nếu thiếu `OPENAI_API_KEY`; Ollama flow không yêu cầu key.
- Tạo ảnh vẫn dùng OpenAI Images API.
- Phải rebuild index khi đổi embedding provider hoặc model.
- Dùng knowledge folder làm reference chính cho các Copilot edits sau này.
- Sau nâng cấp chunking/retrieval, cần rebuild Qdrant collection bằng `docker compose exec app python src/ingest.py` (hoặc nút Train lại toàn bộ trong UI).
- Trang Quản lý Knowledge: sửa file thì train lại file đó, xóa file thì xóa cả vector; dọn vector rác khi file bị xóa ngoài UI.
- Không cần chạy ingest khi chỉ tạo ảnh/Excel hoặc dùng chat memory; chỉ rebuild khi source knowledge/index thay đổi.
