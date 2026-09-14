"""Compare chunk configurations on converted PDF/image Markdown manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc


API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.services.chunking import ChunkConfig, chunk_from_markdown
from app.services.chunking.recursive import approximate_token_count


CONFIGS = {
    "fixed-500-100": ChunkConfig(chunk_size=500, overlap=100),
    "structure-400-50": ChunkConfig(chunk_size=400, overlap=50),
    "structure-300-40": ChunkConfig(chunk_size=300, overlap=40),
}


def _load_manifest(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    documents = raw.get("documents") if isinstance(raw, dict) else raw
    if not isinstance(documents, list) or not documents:
        raise ValueError("Manifest phải là list hoặc object có 'documents' không rỗng")
    return documents


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def benchmark(documents: list[dict]) -> list[dict]:
    reports: list[dict] = []
    for config_name, config in CONFIGS.items():
        all_chunks: list[dict] = []
        start = time.perf_counter()
        tracemalloc.start()
        for item in documents:
            markdown_path = Path(item["markdown_path"])
            source_file = str(item["source_file"])
            markdown = markdown_path.read_text(encoding="utf-8")
            all_chunks.extend(chunk_from_markdown(
                markdown,
                source=source_file,
                file_ext=Path(source_file).suffix,
                config=config,
            ))
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = time.perf_counter() - start
        token_counts = [approximate_token_count(chunk["content"]) for chunk in all_chunks]
        normalized = [_normalized(chunk["content"]) for chunk in all_chunks]
        duplicates = len(normalized) - len(set(normalized))
        pdf_chunks = [
            chunk for chunk in all_chunks
            if Path(str(chunk["metadata"].get("source_file", ""))).suffix.lower() == ".pdf"
        ]
        cited_pdf_chunks = [chunk for chunk in pdf_chunks if chunk["metadata"].get("page_number")]
        reports.append({
            "config": config_name,
            "documents": len(documents),
            "chunks": len(all_chunks),
            "average_tokens": round(statistics.mean(token_counts), 2) if token_counts else 0,
            "max_tokens": max(token_counts, default=0),
            "duplicate_rate": round(duplicates / len(normalized), 4) if normalized else 0,
            "pdf_citation_coverage": round(len(cited_pdf_chunks) / len(pdf_chunks), 4) if pdf_chunks else 1,
            "latency_seconds": round(elapsed, 4),
            "peak_memory_mb": round(peak_memory / 1024 / 1024, 2),
        })
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON gồm source_file và markdown_path")
    parser.add_argument("--json", action="store_true", help="In JSON thay vì bảng")
    args = parser.parse_args()
    try:
        reports = benchmark(_load_manifest(args.manifest))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Benchmark thất bại: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        columns = ("config", "chunks", "average_tokens", "max_tokens", "duplicate_rate", "pdf_citation_coverage", "latency_seconds", "peak_memory_mb")
        print("\t".join(columns))
        for report in reports:
            print("\t".join(str(report[column]) for column in columns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
