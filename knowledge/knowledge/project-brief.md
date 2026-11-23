# Project Brief

## Dự án này là gì

Một local-first personal RAG assistant có nhiệm vụ trả lời câu hỏi từ personal documents, notes, và task files.

## Stack hiện tại

- Python
- Streamlit
- Qdrant (vector database, chạy bằng Docker)
- OpenAI API
- openpyxl

## Luồng runtime chính

1. User nhập prompt trong Streamlit.
2. App lấy semantic candidates từ Qdrant rồi hybrid-rerank bằng lexical relevance và MMR diversity.
3. Context đã retrieve được gửi tới OpenAI chat completions.
4. Answer được render và lưu vào session history; các lượt gần nhất trở thành context cho câu hỏi tiếp theo trong phiên.

Với yêu cầu tạo file, app gọi OpenAI bằng prompt chuyên biệt theo extension. Ảnh được tạo qua Images API và tải PNG; Excel được tạo từ AI structured JSON rồi dựng thành workbook XLSX bằng openpyxl.

## Nguồn dữ liệu

- `data/knowledge/00_personal_project/`
- `data/knowledge/01_learning/`
- `data/knowledge/02_notes/`
- `data/knowledge/03_tasks/`

## Lệnh quan trọng

- Chạy bằng Docker: `docker compose up -d --build`
- Rebuild vectors: `docker compose exec app python src/ingest.py`
- Run app không Docker: `python3 -m streamlit run src/app.py` (cần Qdrant đang chạy ở `QDRANT_URL`)
