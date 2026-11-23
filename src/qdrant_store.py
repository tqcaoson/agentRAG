"""Tầng giao tiếp với Qdrant — vector database thay thế ChromaDB.

Mọi chỗ trong project cần đọc/ghi vector đều đi qua module này, để
ingest.py / query.py / knowledge.py không phải biết chi tiết API Qdrant.

Quy ước lưu trữ:
- Mỗi chunk là 1 point. Point ID là UUID v5 ổn định, sinh từ
  ``"<source>:<chunk_index>:<nội dung chunk>"`` nên ingest lại cùng một
  nội dung sẽ upsert đè đúng point cũ thay vì tạo point trùng.
- Payload của mỗi point gồm:
  - ``source``: đường dẫn tương đối của file gốc, vd
    ``data/knowledge/01_learning/rag_learning_note.md``
  - ``chunk_index``: số thứ tự chunk trong file (int)
  - ``content``: nội dung text của chunk (để xem lại / debug mà không
    cần file gốc)
- Collection dùng khoảng cách COSINE. Kích thước vector lấy theo
  embedding model đang dùng (text-embedding-3-small = 1536,
  nomic-embed-text = 768). Nếu collection cũ có kích thước khác, nó sẽ
  bị xóa và tạo lại vì vector cũ không dùng được với model mới.
"""

import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "") or None
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "home_knowledge")

# Namespace cố định để sinh UUID v5 ổn định cho point ID.
_POINT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Trả về Qdrant client dùng chung (tạo 1 lần, tái sử dụng)."""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client


def reset_qdrant_client() -> None:
    """Đóng và quên client đang cache (dùng khi đổi QDRANT_URL lúc test)."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None


def check_connection() -> tuple[bool, str]:
    """Kiểm tra Qdrant có trả lời không. Trả về (ok, thông báo)."""
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True, f"Đã kết nối Qdrant tại {QDRANT_URL}"
    except Exception as exc:  # noqa: BLE001 - cần hiện lỗi gốc cho user
        return False, f"Không kết nối được Qdrant tại {QDRANT_URL}: {exc}"


def point_id_for(source: str, chunk_index: int, chunk: str) -> str:
    """Sinh UUID ổn định cho 1 chunk (cùng nội dung -> cùng ID)."""
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{source}:{chunk_index}:{chunk}"))


def _source_filter(source: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="source",
                match=models.MatchValue(value=source),
            )
        ]
    )


def collection_exists(client: QdrantClient | None = None) -> bool:
    client = client or get_qdrant_client()
    try:
        return client.collection_exists(QDRANT_COLLECTION)
    except Exception:
        # Client cũ / server cũ: fallback qua danh sách collection.
        names = {c.name for c in client.get_collections().collections}
        return QDRANT_COLLECTION in names


def ensure_collection(vector_size: int, client: QdrantClient | None = None) -> dict:
    """Đảm bảo collection tồn tại với đúng kích thước vector.

    - Chưa có collection -> tạo mới.
    - Có rồi nhưng vector size khác (do đổi embedding model) -> xóa và
      tạo lại, vì vector cũ không tương thích.
    - Có rồi và đúng size -> không làm gì.

    Trả về dict mô tả hành động đã làm (``created`` / ``recreated`` /
    ``exists``) để log ra ngoài.
    """
    client = client or get_qdrant_client()

    if collection_exists(client):
        info = client.get_collection(QDRANT_COLLECTION)
        existing_size = info.config.params.vectors.size
        if existing_size == vector_size:
            return {"action": "exists", "collection": QDRANT_COLLECTION,
                    "vector_size": vector_size}
        client.delete_collection(QDRANT_COLLECTION)
        action = "recreated"
    else:
        action = "created"

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )
    # Index cho field "source" để xóa / đếm / liệt kê chunk theo file nhanh.
    try:
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name="source",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass  # Index đã có hoặc server không hỗ trợ: vẫn chạy được.
    return {"action": action, "collection": QDRANT_COLLECTION,
            "vector_size": vector_size}


def delete_collection(client: QdrantClient | None = None) -> bool:
    """Xóa toàn bộ collection (toàn bộ vector đã train)."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return False
    client.delete_collection(QDRANT_COLLECTION)
    return True


def get_collection_info(client: QdrantClient | None = None) -> dict | None:
    """Thông tin collection: số point, vector size... None nếu chưa có."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return None
    info = client.get_collection(QDRANT_COLLECTION)
    return {
        "collection": QDRANT_COLLECTION,
        "url": QDRANT_URL,
        "points_count": info.points_count,
        "vector_size": info.config.params.vectors.size,
        "distance": str(info.config.params.vectors.distance),
        "status": str(info.status),
    }


def count_points(source: str | None = None,
                 client: QdrantClient | None = None) -> int:
    """Đếm số point (toàn collection, hoặc chỉ của 1 file nguồn)."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return 0
    count_filter = _source_filter(source) if source else None
    result = client.count(
        collection_name=QDRANT_COLLECTION,
        count_filter=count_filter,
        exact=True,
    )
    return result.count


def upsert_chunks(chunks: list[dict], client: QdrantClient | None = None) -> int:
    """Upsert nhiều chunk. Mỗi chunk là dict ``{id, vector, payload}``."""
    if not chunks:
        return 0
    client = client or get_qdrant_client()
    points = [
        models.PointStruct(
            id=item["id"],
            vector=item["vector"],
            payload=item["payload"],
        )
        for item in chunks
    ]
    # Chia lô nhỏ để request không quá lớn khi knowledge nhiều.
    batch_size = 100
    for start in range(0, len(points), batch_size):
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points[start:start + batch_size],
            wait=True,
        )
    return len(points)


def search_similar(query_vector: list[float], limit: int,
                   client: QdrantClient | None = None) -> list[dict]:
    """Tìm các chunk giống vector truy vấn nhất (điểm cosine cao nhất)."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return []
    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    results = []
    for point in response.points:
        payload = point.payload or {}
        results.append({
            "point_id": str(point.id),
            "score": float(point.score),
            "source": payload.get("source", "unknown"),
            "chunk_index": payload.get("chunk_index", 0),
            "content": payload.get("content", ""),
        })
    return results


def scroll_by_source(source: str, limit: int = 1000,
                     client: QdrantClient | None = None) -> list[dict]:
    """Liệt kê mọi chunk của 1 file nguồn, xếp theo chunk_index."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return []
    points, _ = client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=_source_filter(source),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    results = []
    for point in points:
        payload = point.payload or {}
        results.append({
            "point_id": str(point.id),
            "source": payload.get("source", source),
            "chunk_index": payload.get("chunk_index", 0),
            "content": payload.get("content", ""),
        })
    results.sort(key=lambda item: item["chunk_index"])
    return results


def list_indexed_sources(client: QdrantClient | None = None) -> dict[str, int]:
    """Đếm số chunk theo từng file nguồn đang có trong Qdrant.

    Trả về dict ``{source: số chunk}``. Dùng để đối chiếu với file trên
    đĩa và phát hiện vector rác (file đã xóa nhưng vector còn lại).
    """
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return {}
    counts: dict[str, int] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=500,
            offset=offset,
            with_payload=["source"],
            with_vectors=False,
        )
        for point in points:
            source = (point.payload or {}).get("source")
            if source:
                counts[source] = counts.get(source, 0) + 1
        if offset is None:
            break
    return counts


def delete_by_source(source: str, client: QdrantClient | None = None) -> int:
    """Xóa mọi chunk của 1 file nguồn. Trả về số chunk đã xóa."""
    client = client or get_qdrant_client()
    if not collection_exists(client):
        return 0
    deleted = count_points(source=source, client=client)
    if deleted == 0:
        return 0
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=_source_filter(source),
        wait=True,
    )
    return deleted


def delete_point(point_id: str, client: QdrantClient | None = None) -> None:
    """Xóa 1 chunk theo point ID."""
    client = client or get_qdrant_client()
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=[point_id],
        wait=True,
    )
