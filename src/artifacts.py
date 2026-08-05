import base64
import json
import os
import re
from io import BytesIO
from pathlib import Path

import httpx
from openai import OpenAI
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

try:
    from .query import generate_text
except ImportError:  # pragma: no cover
    from query import generate_text


def _history_as_prompt(conversation_history) -> str:
    messages = []
    for item in (conversation_history or [])[-8:]:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append(f"{item['role']}: {item['content']}")
    return "\n".join(messages)


def generate_image_artifact(user_request, conversation_history, artifact_class, filename_inference):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError("OPENAI_API_KEY is missing. Set it in .env before generating images.")

    history = _history_as_prompt(conversation_history)
    prompt = user_request if not history else (
        f"Conversation context:\n{history}\n\nImage request:\n{user_request}"
    )
    client = OpenAI(api_key=api_key)
    response = client.images.generate(
        model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        prompt=prompt,
        size="1024x1024",
        quality=os.getenv("OPENAI_IMAGE_QUALITY", "auto"),
        n=1,
    )
    image_result = response.data[0]
    encoded = getattr(image_result, "b64_json", None)
    image_url = getattr(image_result, "url", None)
    if encoded:
        image_data = base64.b64decode(encoded)
    elif image_url:
        download = httpx.get(image_url, follow_redirects=True, timeout=60.0)
        download.raise_for_status()
        image_data = download.content
    else:
        raise RuntimeError("Image API returned no image data.")

    filename = filename_inference(user_request, default="generated_image.png")
    if Path(filename).suffix.lower() != ".png":
        filename = f"{Path(filename).stem}.png"
    return artifact_class(
        filename=filename,
        data=image_data,
        mime_type="image/png",
        preview=f"Đã tạo ảnh `{filename}` theo yêu cầu của bạn.",
    )


def _safe_sheet_name(name: str, used_names: set[str]) -> str:
    cleaned = re.sub(r"[\\/*?:\[\]]", "_", name).strip()[:31] or "Sheet"
    candidate, counter = cleaned, 2
    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = f"{cleaned[:31-len(suffix)]}{suffix}"
        counter += 1
    used_names.add(candidate)
    return candidate


def build_excel_bytes(specification: dict) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    used_names = set()
    sheets = specification.get("sheets") or []
    if not sheets:
        raise ValueError("AI response did not contain any Excel sheets.")

    for sheet_spec in sheets:
        name = _safe_sheet_name(str(sheet_spec.get("name", "Sheet")), used_names)
        sheet = workbook.create_sheet(name)
        headers = [str(value) for value in sheet_spec.get("headers", [])]
        rows = sheet_spec.get("rows", [])

        if headers:
            sheet.append(headers)
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
                cell.alignment = Alignment(horizontal="center")
            sheet.freeze_panes = "A2"

        for row in rows:
            values = [row.get(header, "") for header in headers] if isinstance(row, dict) else list(row)
            sheet.append(values)

        if headers:
            sheet.auto_filter.ref = sheet.dimensions
        for column_index, column_cells in enumerate(sheet.columns, start=1):
            max_length = max((len(str(cell.value or "")) for cell in column_cells), default=0)
            sheet.column_dimensions[get_column_letter(column_index)].width = min(
                max(max_length + 2, 10), 45
            )

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def generate_excel_artifact(user_request, conversation_history, artifact_class, filename_inference):
    system_prompt = (
        "You design useful Excel workbooks. Return JSON only with this exact shape: "
        '{"sheets":[{"name":"Sheet name","headers":["Column"],"rows":[["value"]]}]}. '
        "Create meaningful realistic data from the request. Keep rows aligned with headers. "
        "Use multiple sheets only when they add clear value."
    )
    raw = generate_text(
        user_request,
        system_prompt,
        temperature=0.3,
        conversation_history=conversation_history,
        response_format={"type": "json_object"},
    )
    try:
        specification = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI returned invalid structured data for Excel.") from exc

    filename = filename_inference(user_request, default="generated_workbook.xlsx")
    if Path(filename).suffix.lower() != ".xlsx":
        filename = f"{Path(filename).stem}.xlsx"
    return artifact_class(
        filename=filename,
        data=build_excel_bytes(specification),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        preview=f"Đã tạo workbook `{filename}` với {len(specification.get('sheets', []))} sheet.",
    )
