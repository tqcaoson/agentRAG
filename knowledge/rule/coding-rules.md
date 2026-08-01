# Coding Rules

## Chung

- Giữ thay đổi nhỏ và cục bộ.
- Ưu tiên code rõ ràng hơn code “thông minh”.
- Không tự bịa ra features không có trong docs hoặc source.
- Khi behavior thay đổi, hãy cập nhật docs.

## Riêng cho RAG

- Xem `data/knowledge/` là source of truth cho local context.
- Rebuild vectors sau khi thay đổi knowledge files.
- Giữ retrieval path và generation path tách biệt, dễ debug.

## Riêng cho UI

- Sidebar actions chỉ nên prefill prompts hoặc thực hiện các hành động rõ ràng.
- Nút Send phải là trigger duy nhất cho model execution.
- Lỗi phải hiển thị trong UI.

## Riêng cho Copilot

- Đọc `knowledge/index.md` trước khi sửa code.
- Ưu tiên các pattern đã có trong `src/`.
- Nếu thay đổi liên quan đến RAG, hãy cập nhật cả architecture và memory notes.
