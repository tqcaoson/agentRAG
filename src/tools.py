import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

try:
    from .query import answer_query, retrieve_context
except ImportError:  # pragma: no cover - fallback for direct script execution
    from query import answer_query, retrieve_context

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_CSV = BASE_DIR / "data" / "knowledge" / "03_tasks" / "personal_tasks.csv"


def search_knowledge_tool(query: str) -> str:
    return answer_query(query)


def infer_generated_filename(prompt: str, default: str = "generated_answer.md") -> str:
    normalized = " ".join(prompt.split()).strip()
    if not normalized:
        return default

    patterns = [
        r"(?:gen|generate|tạo|tao)\s+file\s+([^\n\r,.;:]+)",
        r"(?:file)\s+([^\n\r,.;:]+)",
    ]

    filename = ""
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            filename = match.group(1).strip().split()[0].strip('"\'`')
            break

    if not filename:
        return default

    filename = re.sub(r"[\\/]+", "_", filename)
    filename = re.sub(r"[^A-Za-z0-9._ -]+", "", filename).strip()
    if not filename:
        return default

    if "." not in Path(filename).name:
        filename = f"{filename}.md"

    return filename


def generate_file_from_request(user_request: str) -> str:
    filename = infer_generated_filename(user_request)
    title = Path(filename).stem.replace("_", " ").strip() or "Generated File"
    lines = [
        f"# {title}",
        "",
        "Generated from your request:",
        f"- {user_request}",
        "",
    ]
    return "\n".join(lines)


def summarize_tasks(csv_path: str | None = None) -> str:
    path = Path(csv_path) if csv_path else TASKS_CSV
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    status_counts = {}
    priority_counts = {}
    for row in rows:
        status_counts[row["Status"]] = status_counts.get(row["Status"], 0) + 1
        priority_counts[row["Priority"]] = priority_counts.get(row["Priority"], 0) + 1

    open_tasks = [row for row in rows if row["Status"].lower() != "done"]
    lines = [
        "# Task Summary",
        "",
        "## Status Count",
        f"{status_counts}",
        "",
        "## Priority Count",
        f"{priority_counts}",
        "",
        "## Open Tasks",
    ]
    for row in open_tasks:
        lines.append(f"- {row['Key']}: {row['Summary']} ({row['Priority']})")
    return "\n".join(lines)


def create_weekly_plan() -> str:
    task_summary = summarize_tasks()
    context = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in retrieve_context("personal project current status learning notes risks", top_k=4)
    )
    prompt = f"""
Create a realistic 7-day weekly plan based on the following information.

Task summary:
{task_summary}

Knowledge context:
{context}

Output format:
# Weekly Plan
- Day 1: ...
- Day 2: ...
- Day 3: ...
- Day 4: ...
- Day 5: ...
- Day 6: ...
- Day 7: ...
"""
    return answer_query(prompt)


def create_project_report() -> str:
    context = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in retrieve_context("goal requirements features current status risks", top_k=4)
    )
    prompt = f"""
Create a personal project report from the following context.

Context:
{context}

Return markdown with these sections:
# Personal Project Report

## Goal
## Current Status
## Completed
## Remaining Tasks
## Risks
## Next Actions
"""
    return answer_query(prompt)
