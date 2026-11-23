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
    # Đồng bộ knowledge vào Qdrant ngay lần chạy đầu tiên (chỉ khi
    # Qdrant đang trống; đã có dữ liệu thì bỏ qua để khỏi tốn phí
    # embedding lại). Thử tối đa 3 lần vì lần đầu mạng/API có thể chưa
    # sẵn sàng; nếu cả 3 lần đều lỗi thì app vẫn chạy để user tự train
    # lại sau khi sửa mạng/key.
    echo "Kiem tra knowledge trong Qdrant ..."
    attempt=1
    until python src/ingest.py --if-empty; do
      if [ "$attempt" -ge 3 ]; then
        echo "Canh bao: ingest lan dau that bai sau 3 lan thu."
        echo "Nguyen nhan thuong gap: container khong noi duoc OpenAI API (api.openai.com) hoac OPENAI_API_KEY chua dung."
        echo "App van chay. Kiem tra mang/key roi train lai: docker compose exec app python src/ingest.py"
        break
      fi
      echo "Ingest that bai (lan $attempt/3), thu lai sau 15 giay ..."
      attempt=$((attempt + 1))
      sleep 15
    done
    ;;
  *)
    echo "AUTO_INGEST_ON_START=false, bo qua ingest lan dau."
    ;;
esac

exec "$@"
