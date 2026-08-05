# RAG Workflow Skill

## Mục tiêu

Dùng retrieval từ ChromaDB local kết hợp generation của OpenAI để trả lời câu hỏi dựa trên project data.

## Workflow điển hình

1. Sửa hoặc thêm file trong `data/knowledge/`.
2. Chạy `python src/ingest.py` để rebuild vì chunking có heading context/overlap và vector cũ không tự chuyển đổi.
3. Khởi động app bằng `python3 -m streamlit run src/app.py`.
4. Nhập prompt trong UI.
5. Xem answer và refine source docs nếu cần.

## Prompt hữu ích

- Summarize the project.
- Explain the learning note about RAG.
- Build a weekly plan from current tasks.
- Generate a project report from local context.

## Checklist debug

- Xác nhận `OPENAI_API_KEY` có trong `.env`.
- Xác nhận Chroma collection tồn tại trong `storage/chroma_db`.
- Xác nhận `src/ingest.py` đã chạy thành công.
- Xác nhận app đang đọc đúng prompt và không chỉ cập nhật history.
- Khi retrieval chưa tốt, kiểm tra `RAG_CANDIDATE_K`, `RAG_TOP_K`, và `RAG_MMR_LAMBDA` trước khi đổi prompt.
- Dùng `relevance_score`/`rerank_score` trả về từ `retrieve_context()` để debug thứ tự hybrid retrieval.
