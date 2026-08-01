import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__))

try:
    from .ingest import CHROMA_COLLECTION, CHROMA_PATH, build_index, embed_texts, get_collection
except ImportError:  # pragma: no cover - fallback for direct script execution
    from ingest import CHROMA_COLLECTION, CHROMA_PATH, build_index, embed_texts, get_collection

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def ensure_index_ready():
    collection = get_collection()
    if collection.count() == 0:
        build_index(force=True)


def retrieve_context(query: str, top_k: int = 5):
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    contexts = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        contexts.append(
            {
                "source": metadata.get("source", "unknown"),
                "chunk_index": metadata.get("chunk_index", "0"),
                "content": document,
                "distance": distance,
            }
        )
    return contexts


def format_context(contexts):
    if not contexts:
        return ""

    parts = []
    for context in contexts:
        parts.append(
            f"Source: {context['source']} [chunk {context['chunk_index']}]\n{context['content']}"
        )
    return "\n\n---\n\n".join(parts)


def answer_query(query: str, system_prompt: str | None = None, top_k: int = 5):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError("OPENAI_API_KEY is missing. Set it in .env before asking the assistant.")

    client = OpenAI(api_key=api_key)
    ensure_index_ready()
    contexts = retrieve_context(query, top_k=top_k)
    context_text = format_context(contexts)

    system_message = system_prompt or (
        "You are a personal RAG assistant. Use retrieved context when it helps, but do not limit yourself to it. "
        "If the context is missing or insufficient, answer from your own knowledge and clearly state that the answer is not fully grounded in the current knowledge base. "
        "Be concise, practical, and use markdown where helpful."
    )

    if context_text:
        user_message = f"Context:\n{context_text}\n\nQuestion:\n{query}"
    else:
        user_message = (
            "No relevant context was retrieved from the knowledge base. "
            "Answer the question using your own knowledge, and if useful mention that the answer is not grounded in local documents.\n\n"
            f"Question:\n{query}"
        )

    response = client.chat.completions.create(
        model=DEFAULT_CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content or ""


if __name__ == "__main__":
    result = build_index(force=False)
    print(f"Local vector index ready at {CHROMA_PATH} in collection {CHROMA_COLLECTION}.")
    print(f"Indexed chunks: {result.get('chunks', 'unknown')}")
    print("Type 'exit' to quit.")
    while True:
        question = input("\nAsk: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        print("\nAnswer:\n")
        print(answer_query(question))
