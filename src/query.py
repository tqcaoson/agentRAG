import os
import math
import re
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(__file__))

try:
    from .ingest import CHROMA_COLLECTION, CHROMA_PATH, build_index, embed_texts, get_collection
    from .model_provider import get_client, get_model, get_provider
except ImportError:  # pragma: no cover - fallback for direct script execution
    from ingest import CHROMA_COLLECTION, CHROMA_PATH, build_index, embed_texts, get_collection
    from model_provider import get_client, get_model, get_provider

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
DEFAULT_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "20"))
DEFAULT_MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.75"))


def ensure_index_ready():
    collection = get_collection()
    if collection.count() == 0:
        build_index(force=True)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE)


def _lexical_scores(query: str, documents: list[str]) -> list[float]:
    """BM25 scores over the semantic candidate pool."""
    query_terms = Counter(_tokens(query))
    tokenized = [_tokens(document) for document in documents]
    if not query_terms or not tokenized:
        return [0.0] * len(documents)

    avg_length = sum(map(len, tokenized)) / max(len(tokenized), 1)
    document_frequency = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens) & query_terms.keys())

    scores = []
    for tokens in tokenized:
        frequencies = Counter(tokens)
        score = 0.0
        for term, query_frequency in query_terms.items():
            df = document_frequency[term]
            idf = math.log(1 + (len(tokenized) - df + 0.5) / (df + 0.5))
            tf = frequencies[term]
            denominator = tf + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / max(avg_length, 1))
            score += query_frequency * idf * (tf * 2.5 / denominator if denominator else 0.0)
        scores.append(score)
    return scores


def _normalize(values: list[float], reverse: bool = False) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if math.isclose(low, high):
        return [1.0] * len(values)
    else:
        normalized = [(value - low) / (high - low) for value in values]
    return [1.0 - value for value in normalized] if reverse else normalized


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = set(_tokens(left)), set(_tokens(right))
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def _mmr_select(candidates: list[dict], top_k: int, mmr_lambda: float) -> list[dict]:
    selected: list[dict] = []
    remaining = list(candidates)
    while remaining and len(selected) < top_k:
        def mmr(candidate):
            redundancy = max(
                (_jaccard_similarity(candidate["content"], item["content"]) for item in selected),
                default=0.0,
            )
            return mmr_lambda * candidate["relevance_score"] - (1 - mmr_lambda) * redundancy

        best = max(remaining, key=mmr)
        best["rerank_score"] = mmr(best)
        selected.append(best)
        remaining.remove(best)
    return selected


def retrieve_context(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
    mmr_lambda: float = DEFAULT_MMR_LAMBDA,
):
    ensure_index_ready()
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    available = collection.count()
    candidate_count = min(available, max(top_k, candidate_k))
    if candidate_count == 0:
        return []
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    lexical_scores = _lexical_scores(query, documents)
    semantic_scores = _normalize(distances, reverse=True)
    normalized_lexical = _normalize(lexical_scores)

    contexts = []
    for document, metadata, distance, semantic, lexical in zip(
        documents, metadatas, distances, semantic_scores, normalized_lexical
    ):
        contexts.append(
            {
                "source": metadata.get("source", "unknown"),
                "chunk_index": metadata.get("chunk_index", "0"),
                "content": document,
                "distance": distance,
                "semantic_score": semantic,
                "lexical_score": lexical,
                "relevance_score": 0.7 * semantic + 0.3 * lexical,
            }
        )
    contexts.sort(key=lambda item: item["relevance_score"], reverse=True)
    return _mmr_select(contexts, top_k=top_k, mmr_lambda=mmr_lambda)


def format_context(contexts):
    if not contexts:
        return ""

    parts = []
    for context in contexts:
        parts.append(
            f"Source: {context['source']} [chunk {context['chunk_index']}]\n{context['content']}"
        )
    return "\n\n---\n\n".join(parts)


def _trim_conversation(conversation_history, max_messages: int = 10, max_chars: int = 12000):
    """Keep bounded user/assistant context for the current chat session."""
    history = []
    total_chars = 0
    for message in reversed(conversation_history or []):
        role = message.get("role")
        content = message.get("content", "")
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content:
            continue
        if len(history) >= max_messages or total_chars + len(content) > max_chars:
            break
        history.append({"role": role, "content": content})
        total_chars += len(content)
    return list(reversed(history))


def generate_text(
    prompt: str,
    system_prompt: str,
    temperature: float = 0.4,
    conversation_history=None,
    response_format: dict | None = None,
) -> str:
    provider = get_provider("chat")
    client = get_client(provider)
    request = {
        "model": get_model("chat", provider),
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            *_trim_conversation(conversation_history),
            {"role": "user", "content": prompt},
        ],
    }
    if response_format:
        request["response_format"] = response_format
    response = client.chat.completions.create(**request)
    return response.choices[0].message.content or ""


def answer_query(
    query: str,
    system_prompt: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    conversation_history=None,
):
    rag_enabled = os.getenv("RAG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    contexts = retrieve_context(query, top_k=top_k) if rag_enabled else []
    context_text = format_context(contexts)

    system_message = system_prompt or (
        "You are a personal RAG assistant. Use retrieved context when it helps, but do not limit yourself to it. "
        "If the context is missing or insufficient, answer from your own knowledge and clearly state that the answer is not fully grounded in the current knowledge base. "
        "Be concise, practical, and use markdown where helpful."
    )

    if context_text:
        user_message = f"Context:\n{context_text}\n\nQuestion:\n{query}"
    elif rag_enabled:
        user_message = (
            "No relevant context was retrieved from the knowledge base. "
            "Answer the question using your own knowledge, and if useful mention that the answer is not grounded in local documents.\n\n"
            f"Question:\n{query}"
        )
    else:
        user_message = query

    return generate_text(
        user_message,
        system_message,
        temperature=0.2,
        conversation_history=conversation_history,
    )


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
