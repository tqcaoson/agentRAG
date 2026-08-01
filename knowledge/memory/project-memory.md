# Project Memory

## Durable facts

- Local vector storage là ChromaDB trong `storage/chroma_db`.
- OpenAI chat model default: `gpt-4o-mini`.
- OpenAI embedding model default: `text-embedding-3-small`.
- Streamlit là UI layer.

## Known decisions

- Giữ assistant local-first cho retrieval.
- Chỉ dùng OpenAI cho embeddings và generation.
- Giữ UI đơn giản và dễ debug.
- Sidebar quick prompts chỉ nên prefill prompt input.
- Nút Send phải execute assistant.
- History nên ở trạng thái collapsed cho tới khi mở ra.

## Operational notes

- Rebuild vector database sau khi thay đổi source knowledge.
- App phải fail loudly nếu thiếu `OPENAI_API_KEY`.
- Dùng knowledge folder làm reference chính cho các Copilot edits sau này.
