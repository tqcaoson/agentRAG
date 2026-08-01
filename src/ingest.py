import csv
import hashlib
import os
import re
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "knowledge"
DEFAULT_CHROMA_PATH = BASE_DIR / "storage" / "chroma_db"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(DEFAULT_CHROMA_PATH)))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "home_knowledge")
SUPPORTED_EXTENSIONS = {".md", ".txt", ".csv"}


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


def chunk_text(text: str, max_chars: int = 900):
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs or [normalized]:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars].strip())
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars:
            if current:
                chunks.append(current.strip())
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError("OPENAI_API_KEY is missing. Set it in .env before running RAG.")
    return OpenAI(api_key=api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_client()
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    response = client.embeddings.create(model=embedding_model, input=texts)
    return [item.embedding for item in response.data]


def get_collection():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(name=CHROMA_COLLECTION)


def build_index(force: bool = False):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if force:
        try:
            client.delete_collection(name=CHROMA_COLLECTION)
        except Exception:
            pass

    collection = client.get_or_create_collection(name=CHROMA_COLLECTION)
    if force:
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION)

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

    embeddings = embed_texts(documents)
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

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
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    return {"chunks": len(documents), "collection": CHROMA_COLLECTION}


if __name__ == "__main__":
    result = build_index(force=True)
    print(f"Indexed {result['chunks']} chunks into {result['collection']} at {result['path']}")
