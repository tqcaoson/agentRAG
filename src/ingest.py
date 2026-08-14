import csv
import hashlib
import os
import re
from pathlib import Path

import chromadb
from dotenv import load_dotenv

try:
    from .model_provider import get_client, get_model, get_provider
except ImportError:  # pragma: no cover - fallback for direct script execution
    from model_provider import get_client, get_model, get_provider

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "knowledge"
DEFAULT_CHROMA_PATH = BASE_DIR / "storage" / "chroma_db"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(DEFAULT_CHROMA_PATH)))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "home_knowledge")
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
    response = client.embeddings.create(model=embedding_model, input=texts)
    return [item.embedding for item in response.data]


def get_collection():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(name=CHROMA_COLLECTION)


def build_index(force: bool = False):
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    ids: list[str] = []

    for path in iter_files(DATA_DIR):
        source = str(path.relative_to(BASE_DIR)).replace(os.sep, "/")
        text = load_text(path)
        for chunk_index, chunk in enumerate(chunk_text(text)):
            content_hash = hashlib.sha1(f"{source}:{chunk_index}:{chunk}".encode("utf-8")).hexdigest()
            documents.append(chunk)
            metadatas.append({"source": source, "chunk_index": str(chunk_index)})
            ids.append(content_hash)

    if not documents:
        return {"chunks": 0, "collection": CHROMA_COLLECTION, "path": str(CHROMA_PATH)}

    # Finish the external API operation before replacing a healthy local index.
    embeddings = embed_texts(documents)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if force:
        try:
            client.delete_collection(name=CHROMA_COLLECTION)
        except Exception:
            pass
    collection = client.get_or_create_collection(name=CHROMA_COLLECTION)
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    return {"chunks": len(documents), "collection": CHROMA_COLLECTION, "path": str(CHROMA_PATH)}


def ingest_file(path: Path) -> dict:
    """Ingest a single file into the Chroma collection.

    Returns a dict with number of chunks added and the collection name.
    """
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    collection = get_collection()

    source = str(path.relative_to(BASE_DIR)).replace(os.sep, "/")
    text = load_text(path)
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    ids: list[str] = []

    for chunk_index, chunk in enumerate(chunk_text(text)):
        content_hash = hashlib.sha1(f"{source}:{chunk_index}:{chunk}".encode("utf-8")).hexdigest()
        documents.append(chunk)
        metadatas.append({"source": source, "chunk_index": str(chunk_index)})
        ids.append(content_hash)

    if not documents:
        return {"chunks": 0, "collection": CHROMA_COLLECTION}

    embeddings = embed_texts(documents)
    # Replace all old chunks of this source so edits do not leave stale content behind.
    collection.delete(where={"source": source})
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    return {"chunks": len(documents), "collection": CHROMA_COLLECTION}


if __name__ == "__main__":
    result = build_index(force=True)
    print(f"Indexed {result['chunks']} chunks into {result['collection']} at {result['path']}")
