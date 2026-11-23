import argparse
import csv
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError

try:
    from .model_provider import (
        connection_error_hint,
        get_client,
        get_model,
        get_provider,
    )
    from .qdrant_store import (
        QDRANT_COLLECTION,
        QDRANT_URL,
        count_points,
        delete_by_source,
        delete_collection,
        ensure_collection,
        get_qdrant_client,
        point_id_for,
        upsert_chunks,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from model_provider import (
        connection_error_hint,
        get_client,
        get_model,
        get_provider,
    )
    from qdrant_store import (
        QDRANT_COLLECTION,
        QDRANT_URL,
        count_points,
        delete_by_source,
        delete_collection,
        ensure_collection,
        get_qdrant_client,
        point_id_for,
        upsert_chunks,
    )

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "knowledge"
SUPPORTED_EXTENSIONS = {".md", ".txt", ".csv"}
DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "180"))


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        lines = []
        for row in rows:
            lines.append(" | ".join(f"{key}: {value}" for key, value in row.items()))
        return "\n".join(lines)

    return path.read_text(encoding="utf-8")


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """Split long text near sentence/word boundaries."""
    pieces: list[str] = []
    remaining = text.strip()
    while len(remaining) > max_chars:
        window = remaining[: max_chars + 1]
        boundaries = [window.rfind(marker) for marker in ("\n", ". ", "! ", "? ", "; ", " ")]
        split_at = max(boundaries)
        if split_at < max_chars // 2:
            split_at = max_chars
        elif window[split_at : split_at + 2] in {". ", "! ", "? ", "; "}:
            split_at += 1
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _overlap_tail(text: str, overlap_chars: int) -> str:
    if overlap_chars <= 0 or not text:
        return ""
    tail = text[-overlap_chars:]
    first_space = tail.find(" ")
    return tail[first_space + 1 :].strip() if first_space >= 0 else tail.strip()


def chunk_text(
    text: str,
    max_chars: int = DEFAULT_CHUNK_SIZE,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP,
):
    """Create paragraph-aware chunks with heading context and controlled overlap."""
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""
    current_heading = ""

    for paragraph in paragraphs or [normalized]:
        if paragraph.startswith("#"):
            current_heading = paragraph.splitlines()[0].strip()

        sections = _split_long_text(paragraph, max_chars)
        for section in sections:
            prefix = current_heading if current_heading and not section.startswith(current_heading) else ""
            contextual_section = f"{prefix}\n\n{section}" if prefix else section
            candidate = f"{current}\n\n{contextual_section}" if current else contextual_section
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current and current.strip() != prefix:
                chunks.append(current.strip())
            overlap = _overlap_tail(current, overlap_chars)
            base_parts = [part for part in (prefix, section) if part]
            base = "\n\n".join(dict.fromkeys(base_parts))
            if len(base) > max_chars:
                base = section
            available_overlap = max_chars - len(base) - 2
            if overlap and available_overlap > 20:
                overlap = _overlap_tail(overlap, min(overlap_chars, available_overlap))
                current = "\n\n".join(part for part in (prefix, overlap, section) if part)
                if len(current) > max_chars:
                    current = "\n\n".join(part for part in (overlap, section) if part)
            else:
                current = base

    if current:
        chunks.append(current.strip())

    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = get_provider("embedding")
    client = get_client(provider)
    embedding_model = get_model("embedding", provider)
    try:
        response = client.embeddings.create(model=embedding_model, input=texts)
    except APIConnectionError as exc:
        # SDK chỉ báo "Connection error." nên thêm hướng dẫn cụ thể.
        raise RuntimeError(connection_error_hint(provider)) from exc
    return [item.embedding for item in response.data]


def _relative_source(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace(os.sep, "/")


def _prepare_chunks(path: Path) -> tuple[list[str], list[dict]]:
    """Chunk 1 file, trả về (danh sách chunk text, danh sách payload)."""
    source = _relative_source(path)
    text = load_text(path)
    documents: list[str] = []
    metadatas: list[dict] = []
    for chunk_index, chunk in enumerate(chunk_text(text)):
        documents.append(chunk)
        metadatas.append({
            "source": source,
            "chunk_index": chunk_index,
            "content": chunk,
        })
    return documents, metadatas


def _upsert_embedded(documents: list[str], metadatas: list[dict]) -> int:
    """Embed rồi upsert các chunk vào Qdrant. Trả về số chunk đã ghi."""
    if not documents:
        return 0
    # Embed trước, tạo collection sau: nếu API embedding lỗi thì index
    # cũ vẫn nguyên vẹn, không bị xóa rồi bỏ dở giữa chừng.
    embeddings = embed_texts(documents)
    ensure_collection(vector_size=len(embeddings[0]))
    items = [
        {
            "id": point_id_for(
                metadata["source"], metadata["chunk_index"], document
            ),
            "vector": embedding,
            "payload": metadata,
        }
        for document, metadata, embedding in zip(documents, metadatas, embeddings)
    ]
    return upsert_chunks(items)


def build_index(force: bool = False):
    """Index toàn bộ file trong data/knowledge vào Qdrant.

    ``force=True`` xóa sạch collection trước rồi index lại từ đầu (dùng
    khi đổi embedding model hoặc muốn train lại toàn bộ).
    """
    documents: list[str] = []
    metadatas: list[dict] = []

    for path in iter_files(DATA_DIR):
        docs, metas = _prepare_chunks(path)
        documents.extend(docs)
        metadatas.extend(metas)

    if not documents:
        return {"chunks": 0, "collection": QDRANT_COLLECTION, "url": QDRANT_URL}

    if force:
        delete_collection()
    count = _upsert_embedded(documents, metadatas)

    return {"chunks": count, "collection": QDRANT_COLLECTION, "url": QDRANT_URL}


def ingest_file(path: Path) -> dict:
    """Ingest 1 file vào Qdrant.

    Xóa mọi chunk cũ của file này trước rồi mới upsert chunk mới, để
    nội dung đã sửa không để lại vector cũ. Trả về số chunk đã thêm.
    """
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    documents, metadatas = _prepare_chunks(path)
    if not documents:
        # File rỗng: chỉ dọn vector cũ, không thêm gì.
        delete_by_source(_relative_source(path))
        return {"chunks": 0, "collection": QDRANT_COLLECTION}

    # Embed trước, xóa cũ sau: nếu embedding lỗi thì vector cũ còn nguyên.
    embeddings = embed_texts(documents)
    ensure_collection(vector_size=len(embeddings[0]))
    source = _relative_source(path)
    delete_by_source(source)
    items = [
        {
            "id": point_id_for(
                metadata["source"], metadata["chunk_index"], document
            ),
            "vector": embedding,
            "payload": metadata,
        }
        for document, metadata, embedding in zip(documents, metadatas, embeddings)
    ]
    count = upsert_chunks(items)

    return {"chunks": count, "collection": QDRANT_COLLECTION}


def delete_source(source: str) -> dict:
    """Xóa mọi chunk của 1 file nguồn khỏi Qdrant (không xóa file)."""
    deleted = delete_by_source(source)
    return {"deleted_chunks": deleted, "collection": QDRANT_COLLECTION}


def index_is_empty() -> bool:
    """True khi Qdrant chưa có collection hoặc collection chưa có point."""
    try:
        return count_points(client=get_qdrant_client()) == 0
    except Exception:
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index knowledge files into Qdrant.")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Chỉ index khi collection đang trống (dùng lúc khởi động container).",
    )
    parser.add_argument(
        "--no-force",
        action="store_true",
        help="Không xóa collection trước khi index (mặc định xóa rồi index lại).",
    )
    args = parser.parse_args()

    if args.if_empty and not index_is_empty():
        print(f"Qdrant collection '{QDRANT_COLLECTION}' đã có dữ liệu, bỏ qua ingest.")
    else:
        result = build_index(force=not args.no_force)
        print(f"Indexed {result['chunks']} chunks into {result['collection']} at {result['url']}")
