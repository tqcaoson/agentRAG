# Hướng dẫn sử dụng và training AgentRAG

Giả định bạn đã cài đặt xong theo [HUONG-DAN-CAI-DAT.md](HUONG-DAN-CAI-DAT.md)
và app đang chạy tại http://localhost:8501.

## 1. Tổng quan giao diện

Sidebar bên trái có 2 trang, chuyển qua lại bằng nút radio:

- **💬 Chat** — hỏi đáp, tạo file/ảnh/Excel, thêm tài liệu mới.
- **📚 Quản lý Knowledge** — xem, sửa, xóa tài liệu đã train.

## 2. Chat

### 2.1. Hỏi đáp từ knowledge

Gõ câu hỏi vào ô Prompt rồi bấm **Send**. Ví dụ:

- "Tóm tắt project cá nhân hiện tại của tôi."
- "Tôi đã học được gì về RAG?"
- "Liệt kê các việc cần làm còn chưa xong."

App sẽ tìm chunk liên quan trong Qdrant, rerank bằng BM25 + MMR rồi đưa
vào OpenAI để trả lời. Nếu knowledge không có thông tin, app vẫn trả lời
bằng kiến thức chung của model và nói rõ là không dựa trên tài liệu local.

Sidebar có sẵn 3 quick prompt (Project summary, Learning summary,
Weekly plan): bấm vào để điền sẵn câu hỏi, rồi bấm Send.

### 2.2. Ngữ cảnh hội thoại

App nhớ tối đa 10 lượt user/assistant gần nhất (tối đa 12.000 ký tự)
trong cùng 1 phiên trình duyệt, nên bạn có thể hỏi tiếp kiểu "nói rõ hơn
phần rủi ro đi". Bấm **🗑 Clear chat** để xóa toàn bộ context.

### 2.3. Tạo file, ảnh, Excel

| Muốn làm gì | Gõ ví dụ |
|---|---|
| Tạo file text/markdown | `tạo file story.txt kể một câu chuyện ngắn về robot` |
| Tạo file CSV/JSON/HTML | `tạo file dạng csv gồm danh sách 5 cuốn sách nên đọc` |
| Tạo ảnh PNG | `tạo ảnh robot trong vườn` |
| Tạo Excel | `tạo file plan.xlsx gồm kế hoạch 7 ngày` |

Sau khi tạo xong, app hiện nút **Download** để tải file về. Ảnh tạo bằng
OpenAI Images API nên vẫn cần `OPENAI_API_KEY` dù chat đang dùng Ollama.

### 2.4. Đính kèm file khi chat

Ở khung soạn tin có mục **Attach files**: chọn file rồi bấm Send, file sẽ
được lưu vào `data/knowledge/uploads/` và train ngay trước khi trả lời.
Hữu ích khi muốn hỏi về 1 tài liệu mới mà không cần qua trang quản lý.

## 3. Training — nạp knowledge mới

Knowledge là các file `.md`, `.txt`, `.csv` trong `data/knowledge/`.
Có 3 cách thêm:

### Cách 1 — Upload trong UI (nhanh nhất)

Sidebar → **Add documents** → **Upload files** → chọn file → **Upload &
Ingest**. File được lưu vào `data/knowledge/uploads/` và train ngay.

### Cách 2 — Tạo file trực tiếp trong UI

Sidebar → **Create knowledge file** → chọn thư mục, nhập tên file
(vd `note.md`) và nội dung → **Create & Ingest**.

### Cách 3 — Copy file vào thư mục rồi train

Copy file vào `data/knowledge/` (thư mục có sẵn hoặc thư mục mới tùy ý),
rồi train 1 trong 2 cách:

- Trong UI: trang **Quản lý Knowledge** → file mới hiện trạng thái
  ⏳ **Chưa train** → bấm **🔄 Train lại** ở file đó (hoặc **Train lại
  toàn bộ**).
- Bằng lệnh: `docker compose exec app python src/ingest.py`

**Lưu ý:** chỉ copy file vào thư mục thôi thì chat chưa dùng được — phải
train thì vector mới vào Qdrant. Đây là bước nhiều người quên nhất.

### Training hoạt động thế nào

1. File được cắt thành chunk theo đoạn văn (giữ tiêu đề heading làm ngữ
   cảnh, chồng lấn 180 ký tự ở biên để không mất ý).
2. Mỗi chunk được OpenAI embedding thành vector 1536 chiều.
3. Vector lưu vào Qdrant kèm payload: tên file nguồn, số thứ tự chunk,
   nội dung chunk.
4. Khi hỏi, app tìm chunk giống câu hỏi nhất rồi mới nhờ LLM trả lời.

### Đổi embedding model

Đổi `OPENAI_EMBEDDING_MODEL` (hoặc đổi provider embedding) thì kích thước
vector thay đổi, **bắt buộc** train lại toàn bộ. App tự phát hiện kích
thước khác và xóa collection cũ rồi tạo lại khi bạn chạy ingest.

## 4. Quản lý Knowledge đã train

Mở trang **📚 Quản lý Knowledge** ở sidebar.

### 4.1. Tổng quan

Đầu trang hiện trạng thái Qdrant (đang chạy hay mất kết nối), tên
collection, kích thước vector, model embedding đang dùng, và 4 con số:

- **Tài liệu trên đĩa** — số file trong `data/knowledge/`.
- **Tài liệu đã train** — số file đã có vector trong Qdrant.
- **Tổng vector (chunk)** — tổng số chunk trong Qdrant.
- **Vector rác** — chunk của file đã bị xóa khỏi đĩa nhưng vector còn sót.

### 4.2. Xem tài liệu

Mỗi tài liệu hiện 1 dòng: đường dẫn, số chunk, dung lượng, ngày sửa,
trạng thái (✅ Đã train / ⏳ Chưa train / ❓ Không rõ). Bấm vào để mở rộng:

- **Xem chunk đã train:** mở mục con để xem từng chunk (nội dung + độ
  dài). Đây là cách kiểm tra file đã được cắt/embedding đúng ý chưa.
- **Lọc:** ô tìm theo tên file và dropdown lọc theo thư mục, tiện khi
  knowledge đã nhiều.

### 4.3. Sửa tài liệu

Bấm **✏️ Sửa** → sửa nội dung trong ô text → **💾 Lưu & train lại**.
App ghi đè file gốc, xóa toàn bộ vector cũ của file đó rồi embed lại từ
nội dung mới — nên câu trả lời sau đó dùng ngay nội dung mới, không còn
dính nội dung cũ.

Mẹo: nếu sửa file trực tiếp bằng trình soạn thảo bên ngoài (VS Code...),
vào đây bấm **🔄 Train lại** ở file đó để đồng bộ vector.

### 4.4. Xóa tài liệu

Bấm **🗑 Xóa** → xác nhận lần nữa. App xóa cả file gốc trên đĩa và toàn
bộ vector của file đó trong Qdrant. **Không khôi phục được**, nên cân
nhắc trước khi xóa.

Muốn xóa 1 chunk lẻ (không xóa cả file): mở mục chunk của file, bấm 🗑
ở chunk đó. File gốc giữ nguyên; lưu ý nếu train lại file sau này thì
chunk đó sẽ xuất hiện lại (vì nội dung gốc vẫn còn).

### 4.5. Dọn vector rác

Vector rác sinh ra khi bạn xóa file trực tiếp ngoài thư mục `data/`
(bằng File Explorer / `rm`) mà không qua UI: file mất nhưng vector còn,
nên chat vẫn có thể trả lời từ nội dung của file đã xóa. Bấm
**🧹 Dọn vector rác** để xóa các vector này. Con số vector rác hiện ngay
ở đầu trang để bạn biết khi nào cần dọn.

### 4.6. Train lại toàn bộ

Nút **🔄 Train lại toàn bộ** xóa sạch collection rồi embed lại mọi file.
Dùng khi:

- Đổi embedding model/provider.
- Đổi `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP`.
- Nghi ngờ index bị lệch sau nhiều lần sửa/xóa.
- Vừa copy nhiều file mới vào `data/` cùng lúc.

Việc này tốn phí embedding OpenAI theo tổng dung lượng knowledge, nên
chỉ làm khi cần; sửa 1 file thì chỉ train lại file đó.

### 4.7. Xóa toàn bộ vector (vùng nguy hiểm)

Cuối trang có mục **Xóa toàn bộ vector đã train**: xóa sạch collection
Qdrant, file gốc giữ nguyên. Dùng khi muốn làm sạch index hoàn toàn rồi
train lại sau. Sau khi xóa, chat vẫn chạy nhưng không còn context nào
(app sẽ tự train lại ở câu hỏi đầu tiên nếu `RAG_ENABLED=true`).

## 5. Qdrant Dashboard

Mở http://localhost:6333/dashboard để xem trực tiếp collection
`home_knowledge`: số point, cấu hình vector, và có thể chạy thử search.
Đây là công cụ debug hữu ích khi muốn chắc chắn vector đã vào Qdrant.

## 6. Sao lưu và khôi phục

- **File knowledge:** chỉ cần sao lưu thư mục `data/` (copy đi chỗ khác
  hoặc đưa vào git — trừ `data/knowledge/uploads/` nếu không muốn).
  Đây là nguồn sự thật; mất Qdrant vẫn train lại được từ đây.
- **Vector trong Qdrant:** nằm trong Docker volume `qdrant_storage`.
  Không cần sao lưu riêng nếu còn giữ `data/`, vì train lại là có.
  Nếu vẫn muốn snapshot: Qdrant có API
  `POST http://localhost:6333/collections/home_knowledge/snapshots`
  để tạo snapshot, xem tài liệu Qdrant để khôi phục.
- **`.env`:** giữ key OpenAI cẩn thận, đừng đưa lên git.

## 7. Tinh chỉnh RAG (nâng cao)

Sửa các biến trong `.env` rồi `docker compose up -d` để áp dụng:

| Biến | Tăng lên thì... | Giảm xuống thì... |
|---|---|---|
| `RAG_TOP_K` (mặc định 5) | Thêm context, trả lời đầy đủ hơn nhưng tốn token hơn | Trả lời ngắn gọn, tập trung hơn |
| `RAG_CANDIDATE_K` (mặc định 20) | Rerank có nhiều lựa chọn hơn | Rerank nhanh hơn, ít lựa chọn hơn |
| `RAG_MMR_LAMBDA` (mặc định 0.75) | Ưu tiên chunk liên quan nhất | Ưu tiên chunk đa dạng, ít trùng lặp |
| `RAG_CHUNK_SIZE` (mặc định 1200) | Mỗi chunk chứa nhiều ngữ cảnh hơn | Chunk nhỏ, chính xác hơn nhưng dễ mất ngữ cảnh |

Đổi `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` xong phải **train lại toàn
bộ** thì chunk mới mới có hiệu lực. Đổi `RAG_TOP_K` / `RAG_CANDIDATE_K` /
`RAG_MMR_LAMBDA` thì chỉ cần restart app, không cần train lại.

## 8. Câu hỏi thường gặp

**Hỏi: Sửa file xong mà chat vẫn trả lời theo nội dung cũ?**

Đáp: Bạn chưa train lại file đó. Vào Quản lý Knowledge → bấm Train lại
ở file đó. Sửa bằng nút Sửa trong UI thì đã tự train lại rồi.

**Hỏi: Xóa file ngoài File Explorer rồi mà chat vẫn nhắc tới nó?**

Đáp: Vector rác. Vào Quản lý Knowledge → Dọn vector rác. Lần sau xóa
file bằng nút Xóa trong UI để sạch cả 2 phía.

**Hỏi: Train có tốn phí không?**

Đáp: Có, embedding tính phí theo token qua OpenAI API
(`text-embedding-3-small` rất rẻ, knowledge cá nhân vài MB chỉ tốn vài
nghìn đồng). Chat và tạo ảnh tính phí riêng theo model tương ứng.

**Hỏi: Dùng offline hoàn toàn được không?**

Đáp: Không với cấu hình mặc định, vì chat và embedding gọi OpenAI API
cần mạng. Nếu muốn offline, chuyển `CHAT_PROVIDER` và
`EMBEDDING_PROVIDER` sang `ollama` và chạy Ollama local (cần tải model
`ollama pull llama3.2` và `ollama pull nomic-embed-text`). Tạo ảnh vẫn
cần OpenAI.

**Hỏi: Thêm file PDF / Word được không?**

Đáp: Bản hiện tại chỉ hỗ trợ `.md`, `.txt`, `.csv`. Muốn nạp PDF/Word,
hãy chuyển thành text/markdown trước rồi thêm như file thường.
