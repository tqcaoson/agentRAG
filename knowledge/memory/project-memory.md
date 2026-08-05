# Project Memory

## Durable facts

- Local vector storage là ChromaDB trong `storage/chroma_db`.
- OpenAI chat model default: `gpt-4o-mini`.
- OpenAI embedding model default: `text-embedding-3-small`.
- Streamlit là UI layer.
- OpenAI image model default: `gpt-image-1`.
- Image quality default: `auto`; không gửi `response_format` vì endpoint hiện tại trả base64 mặc định và từ chối tham số này.

## Known decisions

- Giữ assistant local-first cho retrieval.
- Chỉ dùng OpenAI cho embeddings và generation.
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
- App phải fail loudly nếu thiếu `OPENAI_API_KEY`.
- Dùng knowledge folder làm reference chính cho các Copilot edits sau này.
- Sau nâng cấp chunking/retrieval, cần rebuild ChromaDB bằng `python src/ingest.py`.
- Không cần chạy ingest khi chỉ tạo ảnh/Excel hoặc dùng chat memory; chỉ rebuild khi source knowledge/index thay đổi.
