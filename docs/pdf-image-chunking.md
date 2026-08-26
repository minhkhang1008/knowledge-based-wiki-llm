# PDF và image chunking

Pipeline ingestion hiện tại:

```text
PDF/ảnh → structured Markdown → semantic units → bounded chunks
        → batch Ollama embeddings → batch Chroma upsert
```

## Quy tắc chính

- PDF không tạo chunk vượt qua ranh giới trang.
- Heading được đưa vào `heading_path` và lặp ở đầu các child chunk.
- Bảng lớn được chia theo dòng; tiêu đề cột được lặp trong từng chunk.
- OCR ảnh giữ engine, confidence, bbox và số region trong metadata.
- Ảnh không có OCR/caption không tạo vector chỉ chứa tên file.
- Header/footer ngắn lặp trên ít nhất 60% và tối thiểu ba trang bị loại.
- OCR chỉ chạy cho trang thiếu native text hoặc ảnh đủ lớn; kết quả được cache theo hash.
- Vision caption là fallback tùy chọn, mặc định tắt.
- Chunk ID trong Chroma dựa trên content hash. Chunk không đổi tái sử dụng embedding cũ.

## Cấu hình mặc định

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `OLLAMA_EMBED_BATCH_SIZE` | 32 | Số text trong một request embedding |
| `CHROMA_UPSERT_BATCH_SIZE` | 64 | Số chunk trong một lần upsert |
| `OCR_MAX_WORKERS` | 2 | Worker OCR trong một PDF |
| `OCR_CACHE_ENABLED` | true | Bật cache OCR |
| `OCR_EMBEDDED_IMAGES` | true | OCR ảnh nhúng đủ lớn trong PDF |
| `IMAGE_VISION_CAPTION_ENABLED` | false | Dùng vision khi OCR ảnh rỗng |
| `OLLAMA_VISION_MODEL` | llama3.2-vision | Model caption ảnh tùy chọn |

`ChunkConfig` mặc định dùng 400 token, overlap 50 cho PDF text; OCR ảnh dùng 300/30.

## Metadata Chroma

Các field quan trọng gồm `article_id`, `source_file`, `page_number`,
`heading_path`, `block_type`, `bbox`, `ocr_engine`, `ocr_confidence`,
`parent_id`, `child_index`, `content_hash` và `parser_version`.

## Benchmark A/B

Tạo manifest:

```json
{
  "documents": [
    {
      "source_file": "handbook.pdf",
      "markdown_path": "storage/extracted_data/handbook/document.md"
    },
    {
      "source_file": "receipt.png",
      "markdown_path": "storage/extracted_data/receipt/document.md"
    }
  ]
}
```

Chạy từ thư mục `api`:

```powershell
python scripts/benchmark_chunking.py path/to/manifest.json
python scripts/evaluate_retrieval.py
$env:RUN_RAG_INTEGRATION="1"
python scripts/evaluate_retrieval.py --top-k 5
```

Benchmark so sánh 500/100, structure-aware 400/50 và 300/40; báo số chunk,
token trung bình/tối đa, duplicate rate, citation coverage, latency và peak RAM.
Khi có bộ câu hỏi thật, chọn cấu hình dựa trên Recall@5, MRR/citation accuracy,
no-context accuracy, latency và RAM thay vì chỉ nhìn kích thước chunk.

Mục tiêu ban đầu: Recall@5 từ 90%, citation đúng trang từ 95%, no-context từ
90%, duplicate rate dưới 15%, và tuyệt đối không có chunk PDF vượt trang.
