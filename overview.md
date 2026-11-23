# Build RAG Local + AI Agent: MacBook 2014 + Steam Deck + GitHub Copilot

> **Ghi chú (11/2026):** Tài liệu này là bản kế hoạch gốc, giữ lại để tham
> khảo lịch sử. Stack hiện tại đã thay đổi: **ChromaDB → Qdrant** (chạy
> trong Docker, collection `home_knowledge`), cài đặt bằng
> **Docker Compose** (`docker compose up -d --build`), có thêm trang
> **Quản lý Knowledge** trong UI. Tài liệu đúng với code hiện tại là
> `README.md`, `HUONG-DAN-CAI-DAT.md`,
> `HUONG-DAN-SU-DUNG-VA-TRAINING.md` và `knowledge/architect/system-architecture.md`.
> Các đoạn dưới đây còn nhắc ChromaDB / llama-index là nội dung cũ, không
> còn áp dụng.

**Mục tiêu:** Tạo RAG assistant chạy local trên Steam Deck, remote/code từ MacBook, dùng GitHub Copilot để hỗ trợ code. Dùng để tự động hóa việc cá nhân như:

- Hỏi đáp tài liệu học tập
- Hỏi đáp project cá nhân
- Tóm tắt note
- Tạo learning plan, project report, checklist / action items
- Mở rộng thành agent nhỏ sau này

---

## Stack

| Component | Vai trò |
|---|---|
| MacBook 2014 | Remote client / browser / VSCode |
| Steam Deck | Dev machine: Python + ChromaDB + Streamlit |
| GitHub Copilot | Trợ lý viết code |
| OpenAI API hoặc Claude API | LLM + embedding cho RAG |
| ChromaDB | Vector database local |
| LlamaIndex | RAG framework |
| Streamlit | Web UI |

> **Tại sao Steam Deck đủ dùng?**
> Steam Deck có CPU AMD Zen 2 (4c/8t), RAM 16GB, chạy SteamOS (Arch Linux). Đủ để chạy Python, ChromaDB local, Streamlit không lag.

---

## Cấu trúc project

```text
brse-home-rag/
├── data/
│   └── knowledge/
│       ├── 00_personal_project/
│       ├── 01_learning/
│       ├── 02_notes/
│       └── 03_tasks/
├── storage/
│   └── chroma_db/
├── src/
│   ├── __init__.py
│   ├── ingest.py
│   ├── query.py
│   ├── tools.py
│   ├── agent.py
│   └── app.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Phase 0 — Nguyên tắc trước khi làm

**Chỉ dùng dữ liệu cá nhân. Không dùng tài liệu mật công ty.**

Dữ liệu được phép đưa vào RAG:

- Project cá nhân
- Note học tập
- Source code cá nhân
- Tài liệu public
- Markdown tự viết
- Export CSV cá nhân

Bạn cần:

- Steam Deck (máy chạy server)
- MacBook để remote
- GitHub Copilot Student
- API key OpenAI hoặc Claude (nhỏ, chỉ tốn phí khi query)

---

## Phase 1 — Chuẩn bị môi trường trên Steam Deck

### 1.1 Vào Desktop Mode

Trên Steam Deck:

```
Power menu → Switch to Desktop
```

Mở **Konsole** (terminal).

### 1.2 Kiểm tra Python

```bash
python3 --version
pip3 --version
git --version
```

Yêu cầu: Python 3.10 trở lên.

Nếu thiếu pip:

```bash
sudo pacman -S python-pip
```

### 1.3 Bật SSH để remote từ MacBook

```bash
sudo systemctl enable --now sshd
```

Kiểm tra SSH đang chạy:

```bash
sudo systemctl status sshd
```

Lấy IP của Steam Deck:

```bash
ip addr show | grep 'inet ' | grep -v '127.0.0.1'
```

Ghi lại IP dạng `192.168.x.x`.

> **Lưu ý:** Mặc định SteamOS không đặt password cho user `deck`. Cần đặt password trước khi SSH:
>
> ```bash
> passwd
> ```

### 1.4 Tạo thư mục project

```bash
mkdir -p ~/projects
cd ~/projects
mkdir brse-home-rag
cd brse-home-rag
```

### 1.5 Tạo virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Terminal sẽ hiện `(.venv)` — đúng rồi.

Upgrade pip:

```bash
pip install --upgrade pip
```

### 1.6 Tạo `requirements.txt`

```bash
cat > requirements.txt <<'EOF'
chromadb
llama-index
llama-index-vector-stores-chroma
llama-index-llms-openai
llama-index-embeddings-openai
python-dotenv
streamlit
pandas
tabulate
EOF
```

> `tabulate` cần thiết để `df.to_markdown()` hoạt động trong `tools.py`.

Cài dependency:

```bash
pip install -r requirements.txt
```

> ChromaDB local hoàn toàn miễn phí. Chỉ tốn phí khi dùng OpenAI API để embed + query.

---

## Phase 2 — Kết nối MacBook vào Steam Deck

### 2.1 SSH từ MacBook

Đảm bảo MacBook và Steam Deck cùng Wi-Fi.

```bash
ssh deck@<steamdeck-ip>
```

Ví dụ:

```bash
ssh deck@192.168.1.25
```

### 2.2 Remote VSCode qua SSH

Trên MacBook, cài extension:

```
Remote - SSH
```

Kết nối:

```
deck@<steamdeck-ip>
```

Mở folder:

```
~/projects/brse-home-rag
```

### 2.3 Dùng GitHub Copilot

Đăng nhập GitHub trong VSCode để dùng Copilot Student. Copilot giúp code nhưng **không thay thế API runtime** — app vẫn cần OpenAI/Claude API key lúc chạy.

---

## Phase 3 — Tạo cấu trúc project

```bash
# Tạo thư mục
mkdir -p data/knowledge/00_personal_project
mkdir -p data/knowledge/01_learning
mkdir -p data/knowledge/02_notes
mkdir -p data/knowledge/03_tasks
mkdir -p storage/chroma_db
mkdir -p src

# File placeholder để Python nhận src/ là package
touch src/__init__.py
```

Tạo `.gitignore`:

```bash
cat > .gitignore <<'EOF'
.venv/
.env
storage/
__pycache__/
*.pyc
.DS_Store
EOF
```

---

## Phase 4 — Cấu hình API key

Tạo file `.env`:

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

> **Quan trọng:** Không commit `.env` lên GitHub. File này đã có trong `.gitignore`.

Nếu chưa có API key:

- Vẫn có thể viết code trước.
- Nhưng khi chạy ingest + query thật sự cần API key.
- GitHub Copilot chỉ giúp viết code, không thay thế API lúc runtime.

---

## Phase 5 — Tạo dữ liệu mẫu

### 5.1 Project overview mẫu

```bash
cat > data/knowledge/00_personal_project/project_overview.md <<'EOF'
# Personal Project: Habit Tracker App

## Goal

Build a personal habit tracker app to help users track daily habits such as reading, exercise, language learning, and coding practice.

## Main Features

- Create habit
- Mark habit as done
- View daily progress
- View weekly progress
- Export habit history
- Basic notification reminder

## Tech Stack

- Backend: Node.js
- Frontend: React
- Database: SQLite
- Deployment: local first, later cloud

## Current Status

The project is in planning phase. MVP should focus on habit creation, daily tracking, and weekly summary.

## Risks

- Scope creep
- Inconsistent habit data model
- UI complexity
- Lack of notification implementation experience
EOF
```

### 5.2 Requirements mẫu

```bash
cat > data/knowledge/00_personal_project/requirements.md <<'EOF'
# Habit Tracker Requirements

## FEAT-001: Create Habit

Users can create a habit with the following fields:

- habit name
- category
- target frequency
- start date
- optional note

Acceptance Criteria:

- User can create a new habit.
- Habit name is required.
- Category is optional.
- Target frequency must be daily or weekly.

## FEAT-002: Mark Habit As Done

Users can mark a habit as completed for a specific date.

Acceptance Criteria:

- User can mark today's habit as done.
- User can undo completion.
- System must avoid duplicate completion records for the same habit and date.

## FEAT-003: Weekly Summary

Users can view weekly habit progress.

Acceptance Criteria:

- Show total completed habits by week.
- Show completion rate by habit.
- Highlight habits with completion rate lower than 50%.
EOF
```

### 5.3 Note học tập mẫu

```bash
cat > data/knowledge/01_learning/rag_learning_note.md <<'EOF'
# Learning Note: RAG

RAG means Retrieval-Augmented Generation.

## Main Idea

1. Split documents into chunks.
2. Convert chunks into embeddings.
3. Store embeddings in vector database.
4. When user asks a question, retrieve relevant chunks.
5. Send retrieved context plus question to LLM.
6. LLM answers based on retrieved context.

## Benefits

- Can answer based on personal documents.
- Reduces hallucination.
- Useful for project knowledge base.
- Useful for study notes.

## Limitations

- Bad documents lead to bad answers.
- Retrieval can miss relevant context.
- Need evaluation questions to validate quality.
EOF
```

### 5.4 Task CSV mẫu

```bash
cat > data/knowledge/03_tasks/personal_tasks.csv <<'EOF'
Key,Summary,Status,Priority,Area
TASK-001,Setup RAG local environment,Done,High,AI
TASK-002,Create habit tracker requirement,In Progress,High,Project
TASK-003,Build Streamlit UI,To Do,Medium,AI
TASK-004,Write weekly learning summary,To Do,Medium,Learning
TASK-005,Review RAG evaluation questions,To Do,Low,AI
EOF
```

---

## Phase 6 — Build script ingest tài liệu vào ChromaDB

Tạo `src/ingest.py`:

```bash
cat > src/ingest.py <<'EOF'
import os
from dotenv import load_dotenv
import chromadb

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

load_dotenv()

DATA_DIR = "data/knowledge"
PERSIST_DIR = "storage/chroma_db"
COLLECTION_NAME = "home_knowledge"

Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")


def build_index():
    print("Loading documents...")

    documents = SimpleDirectoryReader(
        input_dir=DATA_DIR,
        recursive=True
    ).load_data()

    print(f"Loaded {len(documents)} documents.")

    splitter = SentenceSplitter(
        chunk_size=800,
        chunk_overlap=120
    )

    nodes = splitter.get_nodes_from_documents(documents)

    print(f"Created {len(nodes)} chunks.")

    chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        show_progress=True
    )

    print("Index built successfully.")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Persist dir: {PERSIST_DIR}")


if __name__ == "__main__":
    build_index()
EOF
```

Chạy ingest:

```bash
source .venv/bin/activate
cd ~/projects/brse-home-rag
python src/ingest.py
```

Nếu thành công:

```
Loaded x documents.
Created y chunks.
Index built successfully.
```

> ChromaDB `PersistentClient` tự lưu data xuống `storage/chroma_db` và load lại khi start — không cần làm thêm gì.

---

## Phase 7 — Build script query RAG bằng CLI

Tạo `src/query.py`:

```bash
cat > src/query.py <<'EOF'
import chromadb
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

load_dotenv()

PERSIST_DIR = "storage/chroma_db"
COLLECTION_NAME = "home_knowledge"

Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

SYSTEM_PROMPT = """
You are my personal RAG assistant.

Main role:
- Help with personal projects.
- Help with learning notes.
- Help summarize tasks.
- Help create plans, checklists, and reports.

Rules:
- Answer based on retrieved documents when possible.
- If information is missing, say clearly: "I cannot find this in the current knowledge base."
- Do not invent project facts.
- Prefer structured Markdown output.
- Be concise, practical, and action-oriented.
"""


def load_query_engine():
    chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context
    )

    query_engine = index.as_query_engine(
        similarity_top_k=5,
        response_mode="compact"
    )

    return query_engine


if __name__ == "__main__":
    query_engine = load_query_engine()

    print("Home RAG CLI is ready.")
    print("Type 'exit' to quit.")

    while True:
        question = input("\nAsk: ")

        if question.lower() in ["exit", "quit"]:
            break

        full_prompt = SYSTEM_PROMPT + "\n\nUser question:\n" + question
        response = query_engine.query(full_prompt)

        print("\nAnswer:\n")
        print(response)
EOF
```

Chạy:

```bash
python src/query.py
```

Test bằng các câu:

```
Habit Tracker App hiện có những feature nào?
RAG là gì theo note học tập của tôi?
MVP của habit tracker nên gồm những gì?
Có risk nào trong project habit tracker?
Tạo checklist tuần này để tôi học RAG và build project cá nhân.
```

---

## Phase 8 — Tạo Streamlit UI

Tạo `src/app.py`:

```bash
cat > src/app.py <<'EOF'
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from query import load_query_engine

st.set_page_config(
    page_title="Home RAG Assistant",
    layout="wide"
)

st.title("Home RAG Assistant")
st.caption("Local RAG assistant for personal projects and learning notes")

if "query_engine" not in st.session_state:
    st.session_state.query_engine = load_query_engine()

query_engine = st.session_state.query_engine

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Quick Prompts")

    prompt_project = st.button("📋 Project Summary")
    prompt_learning = st.button("📚 Learning Summary")
    prompt_tasks = st.button("📅 Weekly Plan")
    prompt_risks = st.button("⚠️ Project Risks")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.markdown("""
### Suggested questions

- Habit Tracker App hiện có feature nào?
- Tạo checklist MVP cho project cá nhân.
- Tóm tắt note học RAG của tôi.
- Tạo learning plan 7 ngày.
- Risk chính của project là gì?
    """)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

quick_prompt = None

if prompt_project:
    quick_prompt = "Tóm tắt project cá nhân hiện tại của tôi theo format: Goal, Features, Current Status, Risks, Next Actions."

if prompt_learning:
    quick_prompt = "Tóm tắt các note học tập hiện tại của tôi và tạo danh sách kiến thức cần học tiếp."

if prompt_tasks:
    quick_prompt = "Dựa trên task hiện tại và tài liệu, tạo weekly plan thực tế cho 7 ngày tới."

if prompt_risks:
    quick_prompt = "Phân tích risk của project cá nhân và đề xuất mitigation dạng table."

user_input = st.chat_input("Ask about your personal project, learning notes, tasks...")

final_input = quick_prompt or user_input

if final_input:
    st.session_state.messages.append({
        "role": "user",
        "content": final_input
    })

    with st.chat_message("user"):
        st.markdown(final_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = query_engine.query(final_input)
            answer = str(response)
        st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
EOF
```

Chạy:

```bash
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Mở trên MacBook:

```
http://<steamdeck-ip>:8501
```

Ví dụ:

```
http://192.168.1.25:8501
```

---

## Phase 9 — Dùng GitHub Copilot đúng cách

Trong VSCode, mở **Copilot Chat** và dùng các prompt sau.

**Review code:**

```
Review this RAG project and suggest improvements.
Focus on: code simplicity, error handling, project structure, beginner-friendly improvements.
Do not over-engineer.
```

**Thêm data loader:**

```
Add support for loading markdown, txt, csv files from data/knowledge.
Keep the code simple. Use existing LlamaIndex SimpleDirectoryReader if possible.
```

**Improve Streamlit UI:**

```
Improve src/app.py UI.
Add: sidebar quick prompts, chat history clear button, answer displayed in markdown.
Keep it simple and beginner-friendly.
```

**Tạo agent v0:**

```
Create a simple rule-based agent for this project.
Tools: search_knowledge(query), summarize_tasks(), create_weekly_plan(), create_project_report().
The agent should choose a tool based on user request keyword.
Do not use LangGraph yet.
```

**Debug:**

```
I got this error:
<paste error here>

Explain the root cause and give the minimal fix.
Do not rewrite the whole project unless necessary.
```

---

## Phase 10 — Thêm Agent v0

**Mục tiêu:** Không dùng agent framework phức tạp. Chỉ dùng tool function + router đơn giản — đủ để hiểu agent hoạt động.

Tạo `src/tools.py`:

```bash
cat > src/tools.py <<'EOF'
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from query import load_query_engine

query_engine = load_query_engine()


def search_knowledge(query: str) -> str:
    response = query_engine.query(query)
    return str(response)


def summarize_tasks(csv_path: str = "data/knowledge/03_tasks/personal_tasks.csv") -> str:
    df = pd.read_csv(csv_path)

    status_count = df["Status"].value_counts().to_dict()
    priority_count = df["Priority"].value_counts().to_dict()
    open_tasks = df[df["Status"].str.lower() != "done"]

    result = f"""
# Task Summary

## Status Count

{status_count}

## Priority Count

{priority_count}

## Open Tasks

{open_tasks.to_markdown(index=False)}
"""
    return result


def create_weekly_plan() -> str:
    task_summary = summarize_tasks()
    context = search_knowledge(
        "personal project current status, learning notes, risks, next actions"
    )

    prompt = f"""
Create a realistic 7-day weekly plan based on the following information.

Task summary:
{task_summary}

Knowledge context:
{context}

Output format:
# Weekly Plan

| Day | Focus | Tasks | Expected Output |
|---|---|---|---|

Also include:
- Top 3 priorities
- Risks
- Small daily habit
"""

    response = query_engine.query(prompt)
    return str(response)


def create_project_report() -> str:
    context = search_knowledge(
        "personal project goal, requirements, features, risks, current status"
    )

    prompt = f"""
Create a personal project report based on this context:

{context}

Output format:

# Personal Project Report

## 1. Goal

## 2. Current Status

## 3. Completed

## 4. Remaining Tasks

## 5. Risks

| Risk | Impact | Mitigation |
|---|---|---|

## 6. Next Actions
"""

    response = query_engine.query(prompt)
    return str(response)
EOF
```

Tạo `src/agent.py`:

```bash
cat > src/agent.py <<'EOF'
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tools import (
    search_knowledge,
    summarize_tasks,
    create_weekly_plan,
    create_project_report,
)


def simple_agent(user_request: str) -> str:
    req = user_request.lower()

    if any(k in req for k in ["weekly", "7 ngày", "week", "plan", "kế hoạch"]):
        return create_weekly_plan()

    if any(k in req for k in ["task", "todo", "việc cần làm", "công việc"]):
        return summarize_tasks()

    if any(k in req for k in ["report", "báo cáo", "project summary", "tóm tắt project"]):
        return create_project_report()

    return search_knowledge(user_request)


if __name__ == "__main__":
    print("Simple Home Agent is ready.")
    print("Type 'exit' to quit.")

    while True:
        request = input("\nRequest: ")

        if request.lower() in ["exit", "quit"]:
            break

        result = simple_agent(request)
        print("\nResult:\n")
        print(result)
EOF
```

Chạy:

```bash
python src/agent.py
```

Test:

```
Tạo weekly plan 7 ngày cho tôi
Tóm tắt task hiện tại
Tạo project report
Habit tracker MVP nên làm gì trước?
```

---

## Phase 11 — Tích hợp Agent v0 vào Streamlit

Sau khi `agent.py` chạy ổn, sửa `src/app.py` để dùng agent thay vì query trực tiếp.

Thay dòng import:

```python
# Xóa dòng này:
from query import load_query_engine

# Thêm dòng này:
from agent import simple_agent
```

Xóa:

```python
query_engine = load_query_engine()
```

Thay đoạn xử lý response:

```python
# Xóa:
response = query_engine.query(final_input)
answer = str(response)

# Thành:
answer = simple_agent(final_input)
```

Chạy lại:

```bash
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Bây giờ app có agent router:

| User hỏi | Agent gọi |
|---|---|
| weekly plan / kế hoạch | `create_weekly_plan()` |
| task / việc cần làm | `summarize_tasks()` |
| report / báo cáo | `create_project_report()` |
| Còn lại | `search_knowledge()` |

---

## Phase 12 — Workflow sử dụng hằng ngày

### 12.1 Ghi note mới

Thêm file markdown vào:

```
data/knowledge/01_learning/
data/knowledge/00_personal_project/
data/knowledge/02_notes/
```

Ví dụ tạo daily note:

```bash
cat > data/knowledge/02_notes/2026-07-01_daily_note.md <<'EOF'
# Daily Note - 2026-07-01

## Context

Learning RAG and building local assistant.

## Facts

- ChromaDB runs locally without cost.
- Streamlit provides quick UI.
- Need OpenAI API for LLM response.

## Decisions

- Use ChromaDB first.
- Do not buy GPU laptop now.

## Action Items

| Action | Priority | Status |
|---|---|---|
| Build ingest script | High | Done |
| Build UI | Medium | To Do |

## Risks

- Spending too much time on infra.
- Not enough real data yet.
EOF
```

### 12.2 Re-index

Mỗi lần thêm hoặc sửa nhiều tài liệu:

```bash
python src/ingest.py
```

### 12.3 Mở app

```bash
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Trên MacBook:

```
http://<steamdeck-ip>:8501
```

---

## Phase 13 — Bộ câu hỏi dùng ngay

**Về project cá nhân:**

```
Tóm tắt project cá nhân của tôi.
MVP nên gồm những feature nào?
Risk lớn nhất hiện tại là gì?
Tạo checklist 7 ngày để build MVP.
Requirement nào chưa rõ?
```

**Về học tập:**

```
Tóm tắt note học RAG của tôi.
Tôi nên học gì tiếp theo?
Tạo learning roadmap 2 tuần về RAG và AI Agent.
Giải thích lại RAG dựa trên note của tôi.
```

**Về task:**

```
Tóm tắt task hiện tại.
Task nào priority cao?
Tạo weekly plan 7 ngày.
Tôi nên làm gì tối nay trong 1 tiếng?
```

**Tạo report:**

```
Tạo project report dạng markdown.
Tạo weekly learning report.
Tạo risk report dạng table.
Tạo retrospective tuần này.
```

---

## Phase 14 — Tổ chức knowledge để RAG tốt hơn

Viết markdown theo format chuẩn:

```markdown
# Title

## Context

## Facts

## Decisions

## Action Items

## Risks

## Related Topics
```

**Ví dụ daily note tốt:**

```markdown
# Daily Note - 2026-07-01

## Context

Learning RAG and building local assistant.

## Facts

- ChromaDB runs locally.
- Streamlit provides quick UI.
- Need OpenAI API for LLM response.

## Decisions

- Use ChromaDB first.
- Do not buy GPU laptop now.

## Action Items

| Action | Priority | Status |
|---|---|---|
| Build ingest script | High | Done |
| Build UI | Medium | To Do |

## Risks

- Spending too much time on infra.
- Not enough real data.
```

---

## Phase 15 — Roadmap 7 ngày

| Day | Mục tiêu | Việc cần làm |
|---|---|---|
| Day 1 | Setup | Setup project, install dependencies, tạo sample data, chạy `ingest.py` |
| Day 2 | Test RAG | Chạy `query.py`, test 20 câu hỏi, fix cấu trúc document |
| Day 3 | UI | Build Streamlit UI, mở từ MacBook, thêm quick prompts |
| Day 4 | Tools | Thêm `personal_tasks.csv`, build `tools.py`, build `summarize_tasks()` |
| Day 5 | Agent | Build `agent.py`, thêm weekly plan, thêm project report generator |
| Day 6 | Real data | Thêm note cá nhân thật, re-index, test với workflow thật |
| Day 7 | Polish | Clean README, nhờ Copilot review code, tạo backlog cải tiến tiếp |

---

## Phase 16 — Nâng cấp dần sau khi MVP chạy

### Level 1 — RAG basic (hiện tại)

- Ingest documents
- ChromaDB local
- CLI query
- Streamlit UI

### Level 2 — Agent v0 (hiện tại)

- `search_knowledge()`
- `summarize_tasks()`
- `create_weekly_plan()`
- `create_project_report()`
- Simple keyword router

### Level 3 — Better personal automation

Thêm các tool:

- `summarize_daily_notes()`
- `generate_study_quiz()`
- `create_project_checklist()`
- `create_retrospective()`
- `extract_action_items()`

### Level 4 — LangGraph / LlamaIndex Agent (sau này)

Chỉ học khi:

- Agent v0 quá đơn giản cho nhu cầu thật
- Cần multi-step workflow thật
- Cần tool calling phức tạp
- Cần memory / state tốt hơn

---

## Phase 17 — Vector DB khác (tham khảo)

Giai đoạn này cứ dùng ChromaDB — đủ tốt, local, miễn phí.

Sau này nếu muốn thử:

| DB | Điểm mạnh | Khi nào dùng |
|---|---|---|
| **FAISS** | Nhẹ, nhanh, CPU tốt | Search vector đơn giản, không cần persist |
| **Qdrant** | Production-like, Docker, REST API, metadata filtering | Khi cần tính năng filter phức tạp |

---

## Phase 18 — Troubleshooting

### Lỗi thiếu API key

```
OPENAI_API_KEY not found
```

Kiểm tra:

```bash
cat .env
source .venv/bin/activate
```

Đảm bảo `.env` có:

```env
OPENAI_API_KEY=sk-...
```

### Lỗi module not found

```
ModuleNotFoundError: No module named 'chromadb'
```

Fix:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Lỗi import khi chạy từ thư mục khác

```
ModuleNotFoundError: No module named 'query'
```

Fix: Luôn chạy từ root của project:

```bash
cd ~/projects/brse-home-rag
python src/query.py
```

Hoặc thêm vào đầu script:

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
```

### Streamlit không mở được từ MacBook

Chạy đúng lệnh:

```bash
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Kiểm tra IP:

```bash
ip addr show | grep 'inet '
```

Mở trên MacBook:

```
http://<steamdeck-ip>:8501
```

### RAG trả lời sai hoặc không tìm thấy

Làm theo thứ tự:

1. Kiểm tra tài liệu có nằm trong `data/knowledge/` không
2. Chạy lại `python src/ingest.py`
3. Hỏi câu cụ thể hơn
4. Chia tài liệu dài thành nhiều file markdown nhỏ hơn
5. Thêm heading rõ ràng trong markdown

---

## Phase 19 — Definition of Done

Coi như thành công khi:

- [ ] App mở được trên MacBook qua browser
- [ ] RAG trả lời được dựa trên note cá nhân
- [ ] Thêm markdown mới rồi re-index được
- [ ] Agent v0 tạo được weekly plan
- [ ] Agent v0 tạo được project report
- [ ] Dùng được ít nhất 3 ngày liên tiếp

---

## Phase 20 — Lời khuyên quan trọng

Đừng cố build "siêu agent" ngay.

Bạn chỉ cần bản đầu tiên:

```
RAG + 4 tool:
- search knowledge
- summarize tasks
- create weekly plan
- create project report
```

Nếu bản này giúp tiết kiệm 15–30 phút/ngày, vậy là đáng. Sau đó mới nâng cấp.

---

## Quick Command Summary

```bash
# Vào project và activate venv
cd ~/projects/brse-home-rag
source .venv/bin/activate

# Ingest tài liệu vào ChromaDB
python src/ingest.py

# Test RAG qua CLI
python src/query.py

# Test agent qua CLI
python src/agent.py

# Chạy UI (truy cập từ MacBook qua browser)
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Truy cập UI từ MacBook:

```
http://<steamdeck-ip>:8501
```

---

## README (Tạo cho project)

```bash
cat > README.md <<'EOF'
# brse-home-rag

Personal RAG assistant running on Steam Deck. Remote from MacBook via SSH + VSCode.

## Stack

- Python 3.10+
- ChromaDB (local vector DB)
- LlamaIndex (RAG framework)
- Streamlit (web UI)
- OpenAI API (LLM + embedding)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Điền OPENAI_API_KEY vào .env
```

## Usage

```bash
# Ingest documents
python src/ingest.py

# Query via CLI
python src/query.py

# Run UI
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

## Data

Put personal documents in `data/knowledge/`. Subdirectories:

- `00_personal_project/` — project notes, requirements
- `01_learning/` — learning notes
- `02_notes/` — daily notes
- `03_tasks/` — task CSV files

After adding new documents, re-run `python src/ingest.py`.
EOF
```