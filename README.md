# brse-home-rag

Dự án này là một personal RAG assistant dựa trên kế hoạch trong [agents.md](agents.md). Hệ thống lưu personal knowledge trong các file markdown và CSV cục bộ, index chúng vào ChromaDB local, và dùng OpenAI cho embeddings lẫn answer generation.

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
- `OPENAI_API_KEY` trong file `.env`

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

Điền các biến cần thiết như `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, và `OPENAI_EMBEDDING_MODEL` nếu muốn override mặc định.

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
python src/agent.py &
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

## RAG setup

Project hiện dùng:

- ChromaDB làm local vector database
- OpenAI embeddings để lấy semantic candidate pool
- BM25 lexical scoring kết hợp semantic score để rerank
- MMR selection để giữ context liên quan nhưng giảm các chunk trùng lặp
- OpenAI chat completions để tạo final answer

Các biến tuning tùy chọn nằm trong `.env.example`: `RAG_TOP_K`, `RAG_CANDIDATE_K`, `RAG_MMR_LAMBDA`, `RAG_CHUNK_SIZE`, và `RAG_CHUNK_OVERLAP`.

Yêu cầu như `tạo file story.txt kể một câu chuyện...` hoặc `viết câu chuyện dạng txt...` sẽ sinh nội dung thực bằng AI và hiển thị nút download đúng loại file.

Sau khi thay đổi file trong `data/knowledge/`, hãy chạy lại:

```bash
python src/ingest.py
```

Sau đó mở lại query loop hoặc Streamlit app.

## Ghi chú

- RAG layer cần `OPENAI_API_KEY`.
- Giữ `OPENAI_CHAT_MODEL` và `OPENAI_EMBEDDING_MODEL` trong `.env` nếu muốn đổi default.
- Streamlit UI có thể chạy từ MacBook qua browser khi mở port 8501.

## Copilot knowledge pack

- Project memory và Copilot guidance nằm trong [knowledge/README.md](knowledge/README.md) và [.github/copilot-instructions.md](.github/copilot-instructions.md).
- Hãy giữ các tài liệu này đồng bộ với thay đổi ở RAG flow, UI behavior, hoặc startup commands.
