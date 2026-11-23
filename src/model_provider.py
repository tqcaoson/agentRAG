import os

from openai import OpenAI


SUPPORTED_PROVIDERS = {"openai", "ollama"}


def get_provider(purpose: str) -> str:
    """Return the provider for chat or embeddings, with a shared fallback."""
    provider = os.getenv(f"{purpose.upper()}_PROVIDER", os.getenv("AI_PROVIDER", "openai"))
    provider = provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unsupported {purpose} provider '{provider}'. Use one of: {supported}.")
    return provider


def get_client(provider: str) -> OpenAI:
    if provider == "ollama":
        return OpenAI(
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in .env or switch AI_PROVIDER to ollama."
        )
    return OpenAI(api_key=api_key)


def connection_error_hint(provider: str) -> str:
    """Hướng dẫn khắc phục khi không nối được tới provider.

    OpenAI SDK chỉ báo chung chung "Connection error." nên cần thêm
    ngữ cảnh để user biết phải kiểm tra cái gì.
    """
    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return (
            f"Không kết nối được tới Ollama tại {base_url}. "
            "Kiểm tra Ollama đã chạy chưa ('ollama ps' trên máy host). "
            "Nếu app chạy trong Docker, localhost trong container không phải "
            "máy host: đặt OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 "
            "trong .env và cho Ollama lắng nghe 0.0.0.0 "
            "(OLLAMA_HOST=0.0.0.0:11434, rồi khởi động lại Ollama)."
        )
    return (
        "Không kết nối được tới OpenAI API (api.openai.com). "
        "Kiểm tra mạng/DNS của máy: thử mở https://api.openai.com trên "
        "trình duyệt, kiểm tra VPN/tường lửa, hoặc khởi động lại "
        "Docker Desktop rồi thử lại."
    )


def get_model(purpose: str, provider: str) -> str:
    defaults = {
        ("chat", "openai"): "gpt-4o-mini",
        ("chat", "ollama"): "llama3.2",
        ("embedding", "openai"): "text-embedding-3-small",
        ("embedding", "ollama"): "nomic-embed-text",
    }
    env_name = f"{provider.upper()}_{purpose.upper()}_MODEL"
    return os.getenv(env_name, defaults[(purpose, provider)])
