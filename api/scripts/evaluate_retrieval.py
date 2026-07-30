"""

Đánh giá chất lượng retrieval của hệ thống RAG.

CHẾ ĐỘ CHẠY (2 chế độ):

1) DEFAULT (mặc định, không cần Ollama/ChromaDB thật):
   Dùng một "fake collection" synthetic dựng sẵn trong file này (FAKE_CORPUS) để mô phỏng
   retrieval bằng cách so khớp từ khóa đơn giản. Mục đích: cho phép chạy và tự kiểm tra logic
   evaluate (Recall@k, no-context accuracy) mà không phụ thuộc Ollama/ChromaDB, không cần dữ
   liệu thật đã ingest.

       python scripts/evaluate_retrieval.py

2) INTEGRATION (chỉ chạy khi có biến môi trường RUN_RAG_INTEGRATION=1):
   Gọi thẳng semantic_search_logic thật (Ollama embedding + ChromaDB thật).
   Trước khi chạy, script tự kiểm tra (precheck):
     - ChromaDB (collection "chunks") đã có dữ liệu chưa (count() > 0)?
     - Ollama có đang chạy và phản hồi được không?
   Nếu 1 trong 2 điều kiện trên chưa sẵn sàng (vd: chưa ingest dữ liệu thật, Ollama chưa bật),
   script in thông báo rõ ràng và BỎ QUA (không coi là lỗi/fail, không crash):

       RUN_RAG_INTEGRATION=1 python scripts/evaluate_retrieval.py

Dữ liệu test nằm ở tests/fixtures/retrieval_cases.json — đây là fixture riêng cho script này
(không phải shared mock). Khi có dữ liệu thật từ Squad 1, chỉ cần thay nội dung "cases" trong
file đó, KHÔNG cần đổi logic đánh giá trong file này.

GHI CHÚ CHO PR: khi đã chạy đánh giá (default hoặc integration), chỉ cần mô tả ngắn gọn kết quả
baseline (vd "Recall@5: 8/8, no-context: 3/3") và lựa chọn top_k/threshold đã dùng (script in ra
2 giá trị này cuối phần SUMMARY để copy nhanh vào PR).
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DEFAULT_DATASET_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "retrieval_cases.json"
DEFAULT_TOP_K = 5  # cố định theo yêu cầu "Recall@5"

# Ngưỡng "distance" giả lập dùng cho fake collection ở chế độ default.
# Không liên quan tới RAG_DISTANCE_THRESHOLD thật trong services_vector_db.py.
MOCK_DISTANCE_THRESHOLD = 0.8


# =============================================================================
# FAKE COLLECTION (chế độ DEFAULT) — synthetic, không cần Ollama/ChromaDB
# =============================================================================
FAKE_CORPUS: list[dict[str, Any]] = [
    {
        "text": "Điều kiện hưởng chế độ thai sản gồm thời gian đóng bảo hiểm xã hội tối thiểu.",
        "article_id": "article_001",
        "source_file": None,
        "keywords": ["thai sản", "chế độ thai sản", "điều kiện hưởng"],
    },
    {
        "text": "Mức đóng bảo hiểm xã hội bắt buộc được tính theo phần trăm lương cơ bản.",
        "article_id": "article_002",
        "source_file": None,
        "keywords": ["bảo hiểm xã hội", "mức đóng", "bắt buộc", "phần trăm"],
    },
    {
        "text": "Người lao động có quyền nghỉ phép năm tối thiểu theo quy định của luật lao động.",
        "article_id": "article_003",
        "source_file": None,
        "keywords": ["nghỉ phép năm", "tối thiểu", "ngày phép"],
    },
    {
        "text": "Hồ sơ xin cấp lại sổ bảo hiểm xã hội gồm đơn đề nghị và giấy tờ tùy thân.",
        "article_id": "article_004",
        "source_file": None,
        "keywords": ["hồ sơ", "cấp lại sổ", "bảo hiểm xã hội", "giấy tờ"],
    },
    {
        "text": "Thời gian thử việc tối đa phụ thuộc vào tính chất và mức độ công việc.",
        "article_id": "article_005",
        "source_file": None,
        "keywords": ["thử việc", "tối đa", "thời gian thử việc"],
    },
    {
        "text": "Người lao động được nghỉ phép có hưởng lương khi kết hôn theo chính sách công ty.",
        "article_id": None,
        "source_file": "hr_policy_2024.pdf",
        "keywords": ["kết hôn", "nghỉ khi kết hôn"],
    },
    {
        "text": "Chính sách làm việc từ xa (remote) áp dụng cho các phòng ban đủ điều kiện.",
        "article_id": None,
        "source_file": "hr_policy_2024.pdf",
        "keywords": ["làm việc từ xa", "remote", "chính sách làm việc"],
    },
    {
        "text": "Quy trình phê duyệt chi phí công tác yêu cầu hóa đơn và xác nhận của quản lý.",
        "article_id": None,
        "source_file": "finance_guideline.docx",
        "keywords": ["chi phí công tác", "phê duyệt", "quy trình phê duyệt"],
    },
]


def _normalize(text: str) -> str:
    return text.lower().strip()


def fake_search_similar_chunks(
    query_text: str,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    """
    Bản mô phỏng của search_similar_chunks, dùng FAKE_CORPUS thay cho ChromaDB thật.
    Cùng shape output (text, article_id, source_file, page_number, distance) để
    extract_retrieved_sources() dùng chung logic với chế độ integration.
    """
    normalized_query = _normalize(query_text)

    candidates = FAKE_CORPUS
    if filters:
        candidates = [
            c for c in candidates
            if all(c.get(field) == value for field, value in filters.items() if value)
        ]

    scored: list[dict] = []
    for chunk in candidates:
        score = sum(1 for kw in chunk["keywords"] if kw in normalized_query)
        if score == 0:
            continue

        distance = round(max(0.0, 1 - score / len(chunk["keywords"])), 3)
        if distance > MOCK_DISTANCE_THRESHOLD:
            continue

        scored.append({
            "text": chunk["text"],
            "article_id": chunk["article_id"],
            "source_file": chunk["source_file"],
            "page_number": None,
            "distance": distance,
        })

    scored.sort(key=lambda x: x["distance"])
    return scored[:top_k]


async def fake_semantic_search_logic(
    query_text: str,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    return fake_search_similar_chunks(query_text, top_k=top_k, filters=filters)


# =============================================================================
# INTEGRATION MODE (chỉ chạy khi RUN_RAG_INTEGRATION=1)
# =============================================================================

async def integration_precheck() -> str | None:
    """
    Kiểm tra trước khi chạy integration: ChromaDB có dữ liệu chưa, Ollama có sống không.
    Trả về None nếu sẵn sàng chạy; trả về chuỗi mô tả lý do nếu chưa sẵn sàng (để bỏ qua).
    """
    try:
        from app.services.services_vector_db import collection as real_collection
    except Exception as e:
        return f"Không import được app.services.services_vector_db: {e}"

    try:
        if real_collection.count() == 0:
            return "ChromaDB (collection 'chunks') đang rỗng — chưa có dữ liệu thật được ingest."
    except Exception as e:
        return f"Không kết nối được ChromaDB: {e}"

    try:
        from app.core.ollama_client import chat as ollama_health_check
        await ollama_health_check()
    except Exception as e:
        return f"Không kết nối được Ollama (hoặc model chưa sẵn sàng): {e}"

    return None


# =============================================================================
# Dataset / fixture loading
# =============================================================================

def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file fixture: {path}. "
            "Hãy tạo file tests/fixtures/retrieval_cases.json theo định dạng mô tả trong docstring."
        )

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "cases" in raw:
        data = raw["cases"]
    elif isinstance(raw, list):
        data = raw
    else:
        raise ValueError(
            "Fixture sai định dạng: cần là list case, hoặc object có key 'cases' chứa list case."
        )

    if not data:
        raise ValueError("Dataset rỗng (không có case nào).")

    return data


def extract_retrieved_sources(chunks: list[dict[str, Any]]) -> list[str]:
    sources = []
    for chunk in chunks:
        source = chunk.get("article_id") or chunk.get("source_file")
        if source:
            sources.append(source)
    return sources


def evaluate_case(
    expected_source: str | None,
    expect_no_context: bool,
    retrieved_sources: list[str],
) -> bool:
    if expect_no_context:
        return len(retrieved_sources) == 0

    if not expected_source:
        return False

    return expected_source in retrieved_sources


def format_sources(sources: list[str]) -> str:
    return ", ".join(sources) if sources else "(rỗng)"


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["Question", "Expected source", "Retrieved sources", "Pass/Fail"]

    table_rows = []
    for row in rows:
        table_rows.append([
            row["question"],
            row["expected_source"] if row["expected_source"] else "(no context)",
            format_sources(row["retrieved_sources"]),
            "PASS" if row["passed"] else "FAIL",
        ])

    col_widths = [
        max(len(headers[i]), max((len(r[i]) for r in table_rows), default=0))
        for i in range(len(headers))
    ]

    def format_row(cols: list[str]) -> str:
        return " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(cols))

    separator = "-+-".join("-" * w for w in col_widths)

    print(format_row(headers))
    print(separator)
    for r in table_rows:
        print(format_row(r))


async def run_evaluation(
    dataset: list[dict[str, Any]],
    top_k: int,
    integration_mode: bool,
) -> list[dict[str, Any]]:
    results = []

    if integration_mode:
        from app.services.services_vector_db import semantic_search_logic as search_fn
    else:
        search_fn = fake_semantic_search_logic

    for case in dataset:
        question = case["question"]
        expected_source = case.get("expected_source")
        expect_no_context = bool(case.get("expect_no_context", False))
        filters = case.get("filters")

        try:
            chunks = await search_fn(question, top_k=top_k, filters=filters)
        except Exception as e:
            print(f"⚠️  Lỗi khi truy vấn câu hỏi '{question}': {e}", file=sys.stderr)
            chunks = []

        retrieved_sources = extract_retrieved_sources(chunks)
        passed = evaluate_case(expected_source, expect_no_context, retrieved_sources)

        results.append({
            "question": question,
            "expected_source": expected_source,
            "expect_no_context": expect_no_context,
            "retrieved_sources": retrieved_sources,
            "passed": passed,
        })

    return results


def print_summary(results: list[dict[str, Any]], top_k: int, integration_mode: bool) -> None:
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    context_cases = [r for r in results if not r["expect_no_context"]]
    no_context_cases = [r for r in results if r["expect_no_context"]]

    print("\n=== SUMMARY ===")
    print(f"Chế độ: {'INTEGRATION (dữ liệu thật)' if integration_mode else 'DEFAULT (fake collection / synthetic)'}")
    print(f"top_k = {top_k}, distance_threshold = "
          f"{'RAG_DISTANCE_THRESHOLD thật (xem .env)' if integration_mode else MOCK_DISTANCE_THRESHOLD}")
    print(f"Tổng số case: {total}")
    print(f"Pass: {passed_count}/{total} ({passed_count / total:.1%})")

    if context_cases:
        recall_pass = sum(1 for r in context_cases if r["passed"])
        print(
            f"Recall@{top_k} (câu hỏi có context): "
            f"{recall_pass}/{len(context_cases)} ({recall_pass / len(context_cases):.1%})"
        )
    else:
        print(f"Recall@{top_k}: không có case nào có context để đánh giá.")

    if no_context_cases:
        no_ctx_pass = sum(1 for r in no_context_cases if r["passed"])
        print(
            f"Tỷ lệ nhận diện đúng câu hỏi không có context: "
            f"{no_ctx_pass}/{len(no_context_cases)} ({no_ctx_pass / len(no_context_cases):.1%})"
        )
    else:
        print("Không có case 'expect_no_context' nào để đánh giá.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đánh giá chất lượng retrieval RAG.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Đường dẫn tới file fixture JSON (mặc định: tests/fixtures/retrieval_cases.json)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Số lượng kết quả top-k để đánh giá (mặc định: {DEFAULT_TOP_K})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    integration_mode = os.getenv("RUN_RAG_INTEGRATION") == "1"

    if integration_mode:
        print("=== Chế độ INTEGRATION (RUN_RAG_INTEGRATION=1): dùng Ollama + ChromaDB thật ===")
        problem = asyncio.run(integration_precheck())
        if problem:
            print(f"⚠️  Bỏ qua integration test: {problem}")
            print("   (Chưa sẵn sàng dữ liệu thật/Ollama — không chạy đánh giá integration lần này.)")
            sys.exit(0)
    else:
        print("=== Chế độ DEFAULT: dùng fake collection / dữ liệu synthetic (không cần Ollama/ChromaDB) ===")

    try:
        dataset = load_dataset(args.dataset)
    except (FileNotFoundError, ValueError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)

    results = asyncio.run(run_evaluation(dataset, args.top_k, integration_mode))

    print_table(results)
    print_summary(results, args.top_k, integration_mode)


if __name__ == "__main__":
    main()