#!/bin/sh
# Entrypoint cho container app:
# 1. Đợi Qdrant sẵn sàng (tối đa 60 giây).
# 2. Nếu bật AUTO_INGEST_ON_START và Qdrant đang trống -> train knowledge lần đầu.
# 3. Chạy lệnh chính (Streamlit).
set -e

QDRANT_URL="${QDRANT_URL:-http://qdrant:6333}"

echo "Dang doi Qdrant tai ${QDRANT_URL} ..."
python - "$QDRANT_URL" <<'PYEOF'
import sys
import time
import urllib.error
import urllib.request

url = sys.argv[1].rstrip("/") + "/healthz"
deadline = time.time() + 60
while True:
    try:
        urllib.request.urlopen(url, timeout=3)
        print("Qdrant da san sang.")
        break
    except urllib.error.HTTPError:
        # Server đã trả lời HTTP (dù lỗi mã trạng thái) -> coi như đã lên.
        print("Qdrant da san sang.")
        break
    except Exception:
        if time.time() >= deadline:
            print("Canh bao: het 60s van chua noi duoc Qdrant, van tiep tuc khoi dong app.")
            break
        time.sleep(2)
PYEOF

case "${AUTO_INGEST_ON_START:-true}" in
  true|True|TRUE|1|yes|on)
    echo "Kiem tra knowledge trong Qdrant ..."
    python src/ingest.py --if-empty || echo "Canh bao: ingest lan dau that bai (kiem tra OPENAI_API_KEY). App van chay, co the train lai tu UI."
    ;;
  *)
    echo "AUTO_INGEST_ON_START=false, bo qua ingest lan dau."
    ;;
esac

exec "$@"
