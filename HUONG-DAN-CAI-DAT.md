# Hướng dẫn cài đặt AgentRAG (Docker + Qdrant)

Tài liệu này hướng dẫn cài đặt từ đầu trên máy cá nhân. Máy local chỉ làm
harness (chạy app + Qdrant), LLM dùng OpenAI API nên cần có key OpenAI.

## 1. Chuẩn bị

### 1.1. Docker

- **Windows / macOS:** cài [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  rồi mở Docker Desktop lên và đợi nó báo *Running*.
- **Linux:** cài Docker Engine + Docker Compose plugin theo
  [hướng dẫn chính thức của Docker](https://docs.docker.com/engine/install/).
  Sau khi cài, chạy `docker compose version` để chắc chắn đã có Compose v2.

Kiểm tra Docker đã sẵn sàng:

```bash
docker --version
docker compose version
docker ps
```

`docker ps` chạy được (không báo lỗi kết nối daemon) là đạt.

### 1.2. OpenAI API key

1. Đăng nhập [platform.openai.com](https://platform.openai.com/).
2. Vào **API keys** → **Create new secret key** → copy key (dạng `sk-...`).
3. Tài khoản OpenAI cần có credit/nạp tiền thì API mới gọi được. Key chỉ
   hiện 1 lần lúc tạo, lưu lại cẩn thận.
4. Key chỉ nằm trong file `.env` trên máy bạn, không đưa vào git hay gửi
   cho ai.

### 1.3. Giải nén project

Giải nén file zip ra 1 thư mục, ví dụ:

- Windows: `C:\Users\<bạn>\agentRAG-main`
- macOS/Linux: `~/agentRAG-main`

Mở terminal (Windows: PowerShell hoặc Terminal trong Docker Desktop;
macOS/Linux: Terminal) và vào thư mục đó:

```bash
cd agentRAG-main
```

## 2. Cấu hình

```bash
cp .env.example .env
```

Mở file `.env` bằng trình soạn thảo bất kỳ, sửa dòng:

```env
OPENAI_API_KEY=sk-dien-key-cua-ban-vao-day
```

Các giá trị còn lại để mặc định là chạy được:

- `AI_PROVIDER=openai`
- `OPENAI_CHAT_MODEL=gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`
- `QDRANT_COLLECTION=home_knowledge`
- `QDRANT_URL=http://localhost:6333` — khi chạy bằng Compose, app trong
  container tự dùng `http://qdrant:6333` nên bạn không cần sửa dòng này.

## 3. Chạy lần đầu

```bash
docker compose up -d --build
```

Lệnh này:

1. Build image cho app (lần đầu mất vài phút do tải package Python).
2. Tải image Qdrant `qdrant/qdrant:v1.11.3`.
3. Khởi động 2 container: `agentrag-app` và `agentrag-qdrant`.
4. App đợi Qdrant sẵn sàng rồi tự train knowledge mẫu trong
   `data/knowledge/` (vì Qdrant đang trống).

Theo dõi log lần đầu chạy:

```bash
docker compose logs -f app
```

Thấy dòng `Indexed ... chunks into home_knowledge` và
`You can now view your Streamlit app in your browser` là xong.
Bấm `Ctrl+C` để thoát xem log (container vẫn chạy nền).

## 4. Kiểm tra

| Kiểm tra | Cách làm | Kết quả đạt |
|---|---|---|
| Container đang chạy | `docker compose ps` | Cả 2 service `running` (app `healthy` sau ~40 giây) |
| App | Mở http://localhost:8501 | Thấy giao diện Home RAG Assistant |
| Qdrant | Mở http://localhost:6333/dashboard | Thấy collection `home_knowledge` với số point > 0 |
| Chat | Hỏi: "Tóm tắt project cá nhân hiện tại của tôi." | Trả lời đúng nội dung trong `data/knowledge/00_personal_project/` |

## 5. Các lệnh vận hành hàng ngày

```bash
docker compose up -d              # khởi động lại sau khi tắt máy
docker compose down               # dừng (giữ nguyên dữ liệu Qdrant)
docker compose down -v            # dừng + XÓA dữ liệu Qdrant (train lại từ đầu)
docker compose logs -f app        # xem log app
docker compose logs -f qdrant     # xem log Qdrant
docker compose restart app        # khởi động lại riêng app
docker compose up -d --build app  # build lại app sau khi sửa code
docker compose exec app python src/ingest.py   # train lại toàn bộ knowledge
```

## 6. Cập nhật code / cấu hình

- **Sửa code trong `src/`:** chạy `docker compose up -d --build app`
  để build lại image. (Code được copy vào image lúc build, không mount
  trực tiếp, nên sửa code xong phải build lại.)
- **Sửa file knowledge trong `data/`:** không cần build lại. Thư mục
  `data` được mount trực tiếp vào container; sửa file xong chỉ cần train
  lại file đó (trong UI trang Quản lý Knowledge, hoặc lệnh ingest).
- **Sửa `.env`:** chạy `docker compose up -d` để container nhận biến mới
  (Compose đọc `.env` lúc tạo container). Đổi embedding model thì nhớ
  train lại toàn bộ.

## 7. Lỗi thường gặp

### `docker: command not found` / `docker compose` báo lỗi

Docker chưa được cài hoặc chưa chạy. Mở Docker Desktop và đợi trạng thái
*Running*, rồi chạy lại lệnh trong terminal mới.

### App báo `OPENAI_API_KEY is missing`

File `.env` chưa có key thật, hoặc key vẫn là `your_openai_api_key_here`.
Kiểm tra `.env`, sửa key, rồi chạy `docker compose up -d` để tạo lại
container với biến mới.

### App báo `Incorrect API key` / `401`

Key sai hoặc đã bị thu hồi. Tạo key mới trên platform.openai.com, cập nhật
`.env`, rồi `docker compose up -d`.

### App báo `You exceeded your current quota` / `429`

Tài khoản OpenAI hết credit. Nạp thêm credit rồi thử lại. Chat và
embedding đều tính phí theo lượng dùng của OpenAI.

### `docker compose up` báo port `8501` / `6333` đã bị chiếm

Đã có chương trình khác dùng port đó. Tìm và tắt chương trình đó, hoặc đổi
port phía host trong `docker-compose.yml`, ví dụ `"8502:8501"`, rồi chạy
lại và mở http://localhost:8502.

### Qdrant không lên / app đợi Qdrant quá 60 giây

Xem log Qdrant: `docker compose logs qdrant`. Thường do máy hết RAM/disk
hoặc volume cũ bị lỗi. Thử `docker compose down -v` rồi `up` lại (lưu ý:
mất toàn bộ vector, phải train lại — file gốc trong `data/` không mất).

### Build image lỗi mạng / timeout khi `pip install`

Mạng yếu hoặc bị chặn tới PyPI. Chạy lại `docker compose up -d --build`.
Nếu vẫn lỗi, kiểm tra proxy/VPN của máy.

### Lỗi kết nối Qdrant dạng `InvalidURL` / `Invalid port` (chỉ khi chạy không Docker)

Máy của bạn đang đặt biến proxy (`HTTP_PROXY` / `NO_PROXY`) mà thư viện
HTTP không đọc được. Thêm `localhost` vào `NO_PROXY`, hoặc tắt proxy cho
lần chạy đó rồi thử lại. Khi chạy bằng Docker Compose thì container
không bị ảnh hưởng vì không kế thừa biến proxy của máy host.

### Chat trả lời nhưng không dùng knowledge của tôi

Qdrant đang trống hoặc collection chưa được train. Vào trang
**Quản lý Knowledge** kiểm tra số vector; nếu bằng 0, bấm
**Train lại toàn bộ**. Cũng kiểm tra `RAG_ENABLED` trong `.env` phải là
`true`.

### Muốn chạy lại từ đầu hoàn toàn sạch

```bash
docker compose down -v
docker compose up -d --build
```

Lệnh này xóa container, volume Qdrant và build lại image. File knowledge
trong `data/` và `.env` không bị ảnh hưởng.
