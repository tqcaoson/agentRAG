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
# Loại bỏ ký tự \r (line ending CRLF của Windows) nếu file bị chuyển
# đổi trên máy Windows: nếu không, shebang thành "#!/bin/sh\r" và
# container lỗi "exec ./docker-entrypoint.sh: no such file or directory"
# vì Linux không tìm thấy trình thông dịch "/bin/sh\r".
RUN sed -i 's/\r$//' ./docker-entrypoint.sh && chmod +x ./docker-entrypoint.sh

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=5)"

# Gọi qua sh thay vì dựa vào shebang, để entrypoint vẫn chạy được ngay
# cả khi dòng shebang bị hỏng (vd file có BOM hoặc line ending lạ).
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
