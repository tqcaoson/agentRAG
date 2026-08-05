import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

try:
    from .query import answer_query, generate_text, retrieve_context
except ImportError:  # pragma: no cover - fallback for direct script execution
    from query import answer_query, generate_text, retrieve_context

BASE_DIR = Path(__file__).resolve().parent.parent
TASKS_CSV = BASE_DIR / "data" / "knowledge" / "03_tasks" / "personal_tasks.csv"
GENERATABLE_EXTENSIONS = {"txt", "md", "csv", "json", "html"}


def search_knowledge_tool(query: str) -> str:
    return answer_query(query)


def is_file_generation_request(prompt: str) -> bool:
    normalized = " ".join(prompt.lower().split())
    explicit_file = any(
        phrase in normalized
        for phrase in ("gen file", "generate file", "tạo file", "tao file")
    )
    mentions_format = bool(
        re.search(r"\b(?:dạng|dang|format|định dạng|dinh dang)\s+(?:\.|)(txt|md|csv|json|html)\b", normalized)
        or re.search(r"\.(txt|md|csv|json|html)\b", normalized)
    )
    generation_intent = bool(re.search(r"\b(gen|generate|tạo|tao|viết|viet)\b", normalized))
    return explicit_file or (generation_intent and mentions_format)


def infer_generated_filename(prompt: str, default: str = "generated_answer.md") -> str:
    normalized = " ".join(prompt.split()).strip()
    if not normalized:
        return default

    explicit_filename = re.search(
        r"(?<![\w.])([A-Za-z0-9][A-Za-z0-9._-]*\.(?:txt|md|csv|json|html))\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if explicit_filename:
        filename = explicit_filename.group(1).strip()
        return re.sub(r"[^A-Za-z0-9._-]+", "", filename) or default

    format_match = re.search(
        r"\b(?:dạng|dang|format|định dạng|dinh dang|file)\s+(?:\.|)(txt|md|csv|json|html)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if format_match:
        return f"generated_content.{format_match.group(1).lower()}"

    patterns = [r"(?:gen|generate|tạo|tao)\s+file\s+([^\n\r,.;:]+)"]

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
    extension = Path(filename).suffix.lower() or ".md"
    format_guidance = {
        ".txt": "Return polished plain text only. Do not use Markdown headings or code fences.",
        ".md": "Return valid, well-structured Markdown only. Do not wrap it in a code fence.",
        ".csv": "Return valid CSV only, including a header row. Do not use a code fence or commentary.",
        ".json": "Return valid JSON only. Do not use a code fence or commentary.",
        ".html": "Return a complete, valid HTML document only. Do not use a code fence.",
    }.get(extension, "Return only the complete file content, without a code fence or commentary.")

    system_prompt = (
        "You are a professional content creator. Create the actual requested file content, not a description, "
        "template, acknowledgement, or repetition of the request. Infer a sensible structure, language, tone, "
        "and level of detail from the user's request. If details are missing, make coherent creative choices. "
        f"The target filename is {filename}. {format_guidance}"
    )
    content = generate_text(user_request, system_prompt, temperature=0.7).strip()
    fenced = re.fullmatch(r"```(?:\w+)?\s*\n([\s\S]*?)\n```", content)
    return fenced.group(1).strip() if fenced else content


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
