# Copilot Instructions

Hãy dùng các file trong `knowledge/` làm primary project memory.

## Đọc trước

- `knowledge/index.md`
- `knowledge/knowledge/project-brief.md`
- `knowledge/architect/system-architecture.md`
- `knowledge/rule/coding-rules.md`
- `knowledge/skill/rag-workflow.md`
- `knowledge/memory/project-memory.md`

## Bối cảnh dự án

- App là một personal RAG assistant.
- Local vector storage là ChromaDB tại `storage/chroma_db`.
- OpenAI được dùng cho embeddings và answer generation.
- Streamlit là UI layer.
- Giữ implementation đơn giản, rõ ràng, và dễ debug.

## Hướng dẫn khi chỉnh sửa

- Ưu tiên thay đổi nhỏ và đúng trọng tâm.
- Không tự thêm features không có trong project notes.
- Khi thay đổi RAG behavior, hãy cập nhật luôn các file knowledge liên quan.
- Giữ prompts, rules, và architecture docs đồng bộ với code changes.
