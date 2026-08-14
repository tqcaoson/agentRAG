# brse-home-rag

Dự án này là một personal RAG assistant. Hệ thống lưu personal knowledge trong các file markdown và CSV cục bộ, index chúng vào ChromaDB local, và hỗ trợ OpenAI hoặc Ollama local cho embeddings và answer generation.

## Mục tiêu

- Hỏi đáp từ project notes, learning notes, daily notes, và task data cá nhân.
- Giữ dữ liệu local-first, dễ debug, và dễ mở rộng.
- Dùng cùng một knowledge base cho CLI, Streamlit UI, và agent v0.

## Cấu trúc

- `data/knowledge/`: personal project notes, learning notes, daily notes, task data
- `src/`: Python modules cho ingestion, query, agent, và Streamlit app
- `storage/`: dữ liệu ChromaDB được persist

## Yêu cầu trước khi setup

- Python 3.10+
- `pip`
- OpenAI API key, hoặc Ollama đang chạy local

## Hướng dẫn setup

1. Tạo virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Cài dependencies.

```bash
pip install --upgrade pip setuptools wheel packaging
pip install --only-binary=:all: libcst
pip install --only-binary=:all: pyarrow
```

```bash
pip install -r requirements.txt
```

3. Tạo hoặc kiểm tra file `.env`.

```bash
cp .env.example .env
```

Chọn provider trong `.env`. Để chạy hoàn toàn local:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_CHAT_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

Để dùng OpenAI API:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Có thể cấu hình hybrid bằng `CHAT_PROVIDER` và `EMBEDDING_PROVIDER`. Hai biến này nhận `openai` hoặc `ollama` và override `AI_PROVIDER`, ví dụ chat API nhưng embeddings local:

```env
AI_PROVIDER=openai
CHAT_PROVIDER=openai
EMBEDDING_PROVIDER=ollama
OPENAI_API_KEY=sk-...
```

4. Đưa tài liệu cá nhân vào `data/knowledge/`.

- `00_personal_project/`: project notes và requirements
- `01_learning/`: learning notes
- `02_notes/`: daily notes
- `03_tasks/`: task files dạng CSV

5. Rebuild vector database.

```bash
python src/ingest.py
```

6. Chạy CLI hoặc Streamlit UI.

```bash
python src/agent.py & streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
python -m streamlit run src/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501
```

## RAG setup

Project hiện dùng:

- ChromaDB làm local vector database
- OpenAI hoặc Ollama embeddings để lấy semantic candidate pool
- BM25 lexical scoring kết hợp semantic score để rerank
- MMR selection để giữ context liên quan nhưng giảm các chunk trùng lặp
- OpenAI hoặc Ollama chat completions để tạo final answer

Các biến tuning tùy chọn nằm trong `.env.example`: `RAG_TOP_K`, `RAG_CANDIDATE_K`, `RAG_MMR_LAMBDA`, `RAG_CHUNK_SIZE`, và `RAG_CHUNK_OVERLAP`.

Đặt `RAG_ENABLED=false` để bỏ qua embeddings/ChromaDB và chat trực tiếp với model đã chọn. Chế độ này hữu ích khi chưa cài embedding model local.

Yêu cầu như `tạo file story.txt kể một câu chuyện...` hoặc `viết câu chuyện dạng txt...` sẽ sinh nội dung thực bằng AI và hiển thị nút download đúng loại file.

- Chat ghi nhớ tối đa 10 user/assistant messages gần nhất trong cùng Streamlit session. Nút Clear chat xóa context này.
- `tạo ảnh robot trong vườn` tạo, preview và cho tải file PNG.
- `tạo file plan.xlsx gồm kế hoạch 7 ngày` tạo workbook Excel thật với dữ liệu do AI sinh.

Sau khi thay đổi file trong `data/knowledge/`, hãy chạy lại:

```bash
python src/ingest.py
```

Không cần chạy ingest khi chỉ dùng chat memory, tạo ảnh hoặc tạo Excel. Lệnh này chỉ rebuild vector index từ source knowledge và cần provider embeddings đang hoạt động.

Sau đó mở lại query loop hoặc Streamlit app.

## Ghi chú

- Khi đổi embedding provider hoặc model, bắt buộc chạy lại `python src/ingest.py` vì vector dimension/model có thể khác nhau.
- Tạo ảnh vẫn dùng OpenAI Images API và cần `OPENAI_API_KEY`; Ollama hỗ trợ chat và embeddings trong project này.
- Đổi provider trong `.env` rồi restart CLI/Streamlit, không cần sửa source code.
- Streamlit UI có thể chạy từ MacBook qua browser khi mở port 8501.

## Copilot knowledge pack

- Project memory và Copilot guidance nằm trong [knowledge/README.md](knowledge/README.md) và [.github/copilot-instructions.md](.github/copilot-instructions.md).
- Hãy giữ các tài liệu này đồng bộ với thay đổi ở RAG flow, UI behavior, hoặc startup commands.
