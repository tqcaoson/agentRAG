"""Quản lý knowledge đã train: liệt kê, xem, sửa, xóa, train lại.

Module này là "sự thật" cho trang Quản lý Knowledge trong UI. Nó nối 2 phía:
- File gốc trên đĩa trong ``data/knowledge/`` (nguồn sự thật về nội dung).
- Vector trong Qdrant (đã train từ file đó, đếm theo payload ``source``).

Mọi thao tác sửa/xóa đều đồng bộ cả 2 phía: sửa file -> train lại file đó,
xóa file -> xóa luôn vector của file đó, để không còn vector cũ sót lại.
"""

import os
from datetime import datetime
from pathlib import Path

try:
    from .model_provider import get_model, get_provider
    from .ingest import (
        BASE_DIR,
        DATA_DIR,
        SUPPORTED_EXTENSIONS,
        build_index,
        delete_source,
        ingest_file,
        iter_files,
    )
    from .qdrant_store import (
        QDRANT_COLLECTION,
        QDRANT_URL,
        check_connection,
        count_points,
        delete_by_source,
        delete_collection,
        delete_point,
        get_collection_info,
        list_indexed_sources,
        scroll_by_source,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from model_provider import get_model, get_provider
    from ingest import (
        BASE_DIR,
        DATA_DIR,
        SUPPORTED_EXTENSIONS,
        build_index,
        delete_source,
        ingest_file,
        iter_files,
    )
    from qdrant_store import (
        QDRANT_COLLECTION,
        QDRANT_URL,
        check_connection,
        count_points,
        delete_by_source,
        delete_collection,
        delete_point,
        get_collection_info,
        list_indexed_sources,
        scroll_by_source,
    )


def _relative_source(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace(os.sep, "/")


def resolve_source(source: str) -> Path:
    """Chuyển ``source`` thành đường dẫn file, chặn path traversal.

    Chỉ cho phép file nằm trong ``data/knowledge/``. Raise ValueError
    nếu source trỏ ra ngoài (vd chứa ``..``).
    """
    candidate = (BASE_DIR / source).resolve()
    data_root = DATA_DIR.resolve()
    if candidate != data_root and data_root not in candidate.parents:
        raise ValueError(f"Đường dẫn không hợp lệ: {source}")
    return candidate


def _validate_filename(filename: str) -> str:
    name = filename.strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Tên file không hợp lệ: {filename!r}")
    if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Chỉ hỗ trợ file {allowed}, nhận được: {name!r}")
    return name


def get_stats() -> dict:
    """Tổng quan hệ thống cho trang quản lý: Qdrant + file trên đĩa."""
    qdrant_ok, qdrant_message = check_connection()
    info = get_collection_info() if qdrant_ok else None
    files = list(iter_files(DATA_DIR)) if DATA_DIR.exists() else []
    indexed = list_indexed_sources() if qdrant_ok else {}
    on_disk = {_relative_source(path) for path in files}
    orphans = {
        source: chunks
        for source, chunks in indexed.items()
        if source not in on_disk
    }
    return {
        "qdrant_ok": qdrant_ok,
        "qdrant_message": qdrant_message,
        "qdrant_url": QDRANT_URL,
        "collection": QDRANT_COLLECTION,
        "vector_size": info["vector_size"] if info else None,
        "points_count": info["points_count"] if info else 0,
        "docs_on_disk": len(files),
        "docs_indexed": len([s for s in indexed if s in on_disk]),
        "orphan_sources": orphans,
        "orphan_chunks": sum(orphans.values()),
        "embedding_model": _current_embedding_model(),
    }


def _current_embedding_model() -> str:
    """Tên embedding model đang cấu hình (để hiển thị ở UI)."""
    try:
        provider = get_provider("embedding")
        return get_model("embedding", provider)
    except Exception:
        return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def list_documents() -> list[dict]:
    """Liệt kê mọi file knowledge trên đĩa kèm số chunk đã train.

    Mỗi item gồm: source, tên file, thư mục, kích thước, ngày sửa,
    số chunk trong Qdrant (None nếu không nối được Qdrant) và trạng thái:
    ``indexed`` (đã train), ``not_indexed`` (chưa train / 0 chunk),
    ``unknown`` (không kiểm tra được Qdrant).
    """
    try:
        indexed = list_indexed_sources()
        qdrant_available = True
    except Exception:
        indexed = {}
        qdrant_available = False

    documents = []
    if DATA_DIR.exists():
        for path in iter_files(DATA_DIR):
            source = _relative_source(path)
            stat = path.stat()
            chunks = indexed.get(source, 0) if qdrant_available else None
            if not qdrant_available:
                status = "unknown"
            elif chunks and chunks > 0:
                status = "indexed"
            else:
                status = "not_indexed"
            documents.append({
                "source": source,
                "name": path.name,
                "folder": str(path.parent.relative_to(DATA_DIR)).replace(os.sep, "/"),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                "chunks": chunks,
                "status": status,
            })
    documents.sort(key=lambda item: (item["folder"], item["name"]))
    return documents


def read_document(source: str) -> str:
    """Đọc nội dung gốc của 1 file knowledge (để hiển thị / sửa)."""
    path = resolve_source(source)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file: {source}")
    return path.read_text(encoding="utf-8")


def save_document(source: str, content: str) -> dict:
    """Ghi đè nội dung file rồi train lại file đó trong Qdrant."""
    path = resolve_source(source)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file: {source}")
    path.write_text(content, encoding="utf-8")
    result = ingest_file(path)
    return {"source": source, "chunks": result["chunks"]}


def create_document(folder: str, filename: str, content: str) -> dict:
    """Tạo file knowledge mới rồi train ngay."""
    name = _validate_filename(filename)
    folder = (folder or "uploads").strip().strip("/")
    if not folder or ".." in Path(folder).parts:
        raise ValueError(f"Thư mục không hợp lệ: {folder!r}")
    target_dir = DATA_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / name
    if dest.exists():
        raise FileExistsError(f"File đã tồn tại: {dest.name} trong {folder}")
    dest.write_text(content, encoding="utf-8")
    result = ingest_file(dest)
    return {"source": _relative_source(dest), "chunks": result["chunks"]}


def delete_document(source: str) -> dict:
    """Xóa file gốc VÀ toàn bộ vector của file đó khỏi Qdrant."""
    path = resolve_source(source)
    deleted_chunks = delete_by_source(source)
    if path.exists() and path.is_file():
        path.unlink()
    return {"source": source, "deleted_chunks": deleted_chunks}


def reingest_document(source: str) -> dict:
    """Train lại 1 file (sau khi sửa file trực tiếp ngoài UI)."""
    path = resolve_source(source)
    result = ingest_file(path)
    return {"source": source, "chunks": result["chunks"]}


def reingest_all() -> dict:
    """Train lại toàn bộ knowledge (xóa sạch collection rồi index lại)."""
    return build_index(force=True)


def list_chunks(source: str) -> list[dict]:
    """Liệt kê các chunk đã train của 1 file (để xem / xóa từng chunk)."""
    return scroll_by_source(source)


def delete_chunk(point_id: str) -> None:
    """Xóa 1 chunk khỏi Qdrant (không đụng tới file gốc)."""
    delete_point(point_id)


def find_orphans() -> list[dict]:
    """Tìm vector rác: source có trong Qdrant nhưng file đã bị xóa."""
    indexed = list_indexed_sources()
    on_disk = (
        {_relative_source(path) for path in iter_files(DATA_DIR)}
        if DATA_DIR.exists()
        else set()
    )
    return [
        {"source": source, "chunks": chunks}
        for source, chunks in sorted(indexed.items())
        if source not in on_disk
    ]


def delete_orphans() -> dict:
    """Xóa toàn bộ vector rác. Trả về số source và số chunk đã dọn."""
    orphans = find_orphans()
    deleted_chunks = 0
    for item in orphans:
        deleted_chunks += delete_by_source(item["source"])
    return {"sources": len(orphans), "deleted_chunks": deleted_chunks}


def delete_all_vectors() -> bool:
    """Xóa toàn bộ vector đã train (file gốc giữ nguyên)."""
    return delete_collection()


def count_chunks(source: str | None = None) -> int:
    """Đếm chunk: toàn collection hoặc của 1 file."""
    return count_points(source=source)


__all__ = [
    "create_document",
    "delete_all_vectors",
    "delete_chunk",
    "delete_document",
    "delete_orphans",
    "find_orphans",
    "get_stats",
    "list_chunks",
    "list_documents",
    "read_document",
    "reingest_all",
    "reingest_document",
    "resolve_source",
    "save_document",
    "count_chunks",
    "delete_source",
]
