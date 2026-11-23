# AgentRAG — Streamlit app (harness chạy local, LLM dùng OpenAI API)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài dependencies trước để tận dụng Docker layer cache: sửa code
# không phải cài lại package.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY .streamlit/ ./.streamlit/
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=5)"

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
