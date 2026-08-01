# Project Brief

## Dự án này là gì

Một local-first personal RAG assistant có nhiệm vụ trả lời câu hỏi từ personal documents, notes, và task files.

## Stack hiện tại

- Python
- Streamlit
- ChromaDB
- OpenAI API

## Luồng runtime chính

1. User nhập prompt trong Streamlit.
2. App retrieve các chunk phù hợp từ ChromaDB collection local.
3. Context đã retrieve được gửi tới OpenAI chat completions.
4. Answer được render trong app và lưu vào chat history.

## Nguồn dữ liệu

- `data/knowledge/00_personal_project/`
- `data/knowledge/01_learning/`
- `data/knowledge/02_notes/`
- `data/knowledge/03_tasks/`

## Lệnh quan trọng

- Rebuild vectors: `python src/ingest.py`
- Run app: `python3 -m streamlit run src/app.py`
