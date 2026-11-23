# Knowledge Index

## Phạm vi hiện tại

- Personal RAG assistant cho study notes, personal projects, và task summaries.
- Nguồn dữ liệu là các file markdown và CSV local trong `data/knowledge/`.
- Retrieval dùng Qdrant collection `home_knowledge`, chạy trong Docker, dữ liệu lưu ở volume `qdrant_storage`.
- Embeddings và answer generation có thể dùng OpenAI hoặc Ollama local qua cấu hình provider.
- UI dùng Streamlit.

## Tài liệu tham chiếu

- [Project brief](knowledge/project-brief.md)
- [System architecture](architect/system-architecture.md)
- [Coding rules](rule/coding-rules.md)
- [RAG workflow](skill/rag-workflow.md)
- [Project memory](memory/project-memory.md)
