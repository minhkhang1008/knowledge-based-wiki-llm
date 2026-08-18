# Real Retrieval Baseline

## Mục tiêu

Baseline này hoàn tất phần đánh giá retrieval trên dữ liệu thật của Tuần 8. Bộ
dữ liệu synthetic cũ vẫn được giữ nguyên để kiểm tra logic evaluator mà không cần
Ollama hoặc ChromaDB.

## Dữ liệu

- Corpus: `api/tests/fixtures/retrieval_corpus_real.json`
- Cases: `api/tests/fixtures/retrieval_cases_real.json`
- Nguồn: 8 phần nội dung thật từ `squad-2-api-contract.md` trên `develop`
- Repository nguồn: `minhkhang1008/knowledge-based-wiki-llm`
- Ngày lấy dữ liệu: 2026-08-18

Mỗi corpus entry lưu đường dẫn file công khai trong repository và một `article_id`
ổn định cho từng phần contract. Các đoạn có thể đối chiếu trực tiếp với file đang
tồn tại trên `develop`, không phải dữ liệu tự tạo và không công khai thêm dữ liệu
ngoài repository.

Dataset gồm 10 cases:

- 6 cases đối chiếu bằng `article_id`
- 2 cases đối chiếu bằng `source_file`
- 2 cases `expect_no_context=true`

Test `api/tests/test_real_retrieval_baseline.py` kiểm tra tự động số lượng từng
loại case và xác nhận mọi `expected_source` có thật trong metadata của corpus.

## Cách chạy tái lập

Yêu cầu Ollama đang chạy và đã có model `nomic-embed-text`.

Từ thư mục `api`:

```bash
export CHROMA_PERSIST_PATH=/tmp/kbw-real-baseline-chroma
export DATABASE_URL=sqlite+aiosqlite:////tmp/kbw-real-baseline.db
python scripts/seed_retrieval_baseline.py
RUN_RAG_INTEGRATION=1 python scripts/evaluate_retrieval.py \
  --dataset tests/fixtures/retrieval_cases_real.json \
  --top-k 5
```

Seeder upsert 8 Article có ID ổn định vào SQLite và chỉ thay các chunk ID có trong
corpus baseline. Nó không xóa article hoặc chunk khác đang tồn tại. Vì nội dung
Article khớp đoạn đã index, `scripts/check_index_integrity.py` có thể kiểm tra
baseline mà không báo orphan hoặc stale content giả.

## Cấu hình chốt

- Embedding model: `nomic-embed-text`
- Chroma distance: L2 mặc định của collection hiện tại
- `top_k`: `5`
- Embedding normalization: L2 unit norm before index and query
- `RAG_DISTANCE_THRESHOLD`: `0.68`

Ngưỡng không được chọn từ synthetic fixture. Vector thô của `nomic-embed-text`
có độ lớn thay đổi theo input, nên dùng L2 trực tiếp khiến cùng một ngưỡng không
tổng quát được. Embedding nay được chuẩn hóa unit norm trước cả index và query.
Trên dữ liệu thật, khoảng cách của nguồn đúng nằm trong khoảng `0.4428-0.6460`.
Hai câu hỏi ngoài phạm vi có kết quả gần nhất ở `0.7527` và `0.7949`, vì vậy chọn
ngưỡng `0.68`.

## Kết quả ngày 2026-08-18

```text
Recall@5: 8/8 (100.0%)
No-context accuracy: 2/2 (100.0%)
Pass: 10/10 (100.0%)
Technical errors: 0
top_k: 5
RAG_DISTANCE_THRESHOLD: 0.68
Index integrity: 8 chunks, 0 orphan, 0 stale, 0 invalid metadata
```

Ngoài evaluator, smoke test API thật đã xác nhận:

- Article create trả `201`, tự index vào ChromaDB
- Semantic search trả đúng `source_file`
- Article delete xóa đồng bộ SQLite và ChromaDB
- QA trả câu trả lời có citation cùng nguồn `squad-2-api-contract.md`
- QA log được ghi vào SQLite

## Lỗi phát hiện khi chạy thật

Evaluator trước đây chạy health check và evaluation bằng hai event loop riêng
nhưng dùng chung Ollama `AsyncClient`, khiến truy vấn đầu tiên có thể lỗi
`Event loop is closed`. Hai bước nay chạy trong cùng một event loop.

Embedding thô trước đây chưa được chuẩn hóa, khiến khoảng cách L2 phụ thuộc mạnh
vào độ lớn vector và ngưỡng không ổn định giữa các câu hỏi. Embedding hiện được
chuẩn hóa trước khi ghi/query; ngưỡng mặc định là `0.68` và deployment vẫn có thể
override qua biến môi trường.

## Failure còn lại

Không còn case thất bại trong baseline hiện tại. Khi thay model embedding, metric
distance hoặc corpus demo, phải seed lại index và chạy lại baseline trước khi đổi
ngưỡng. Sau khi nhận thay đổi chuẩn hóa này, index cũ cũng phải được tạo lại vì
không được trộn vector thô và vector đã chuẩn hóa trong cùng collection.
