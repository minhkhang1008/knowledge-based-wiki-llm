from __future__ import annotations

import json
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures"
CORPUS_PATH = FIXTURE_DIR / "retrieval_corpus_real.json"
CASES_PATH = FIXTURE_DIR / "retrieval_cases_real.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_cases_meet_week_8_coverage() -> None:
    cases = _load(CASES_PATH)["cases"]

    article_cases = [
        case for case in cases
        if case.get("expected_source_field") == "article_id"
    ]
    source_file_cases = [
        case for case in cases
        if case.get("expected_source_field") == "source_file"
    ]
    no_context_cases = [
        case for case in cases if case.get("expect_no_context") is True
    ]

    assert len(cases) >= 10
    assert len(article_cases) >= 6
    assert len(source_file_cases) >= 2
    assert len(no_context_cases) >= 2
    assert all(case["expected_source"] is None for case in no_context_cases)


def test_every_expected_source_exists_in_real_corpus_metadata() -> None:
    chunks = _load(CORPUS_PATH)["chunks"]
    cases = _load(CASES_PATH)["cases"]

    metadata_values = {
        "article_id": {chunk["article_id"] for chunk in chunks},
        "source_file": {chunk["source_file"] for chunk in chunks},
    }

    for case in cases:
        if case["expect_no_context"]:
            continue

        source_field = case["expected_source_field"]
        assert case["expected_source"] in metadata_values[source_field]


def test_real_corpus_is_traceable_to_public_repository_source() -> None:
    corpus = _load(CORPUS_PATH)
    chunks = corpus["chunks"]

    assert corpus["_meta"]["data_type"] == "real"
    assert corpus["_meta"]["source_path"] == "squad-2-api-contract.md"
    assert len(chunks) == 8
    assert len({chunk["id"] for chunk in chunks}) == len(chunks)
    assert all(
        chunk["source_url"].startswith(
            "https://github.com/minhkhang1008/knowledge-based-wiki-llm/"
        )
        for chunk in chunks
    )
    assert all(chunk["article_id"].startswith("repo-") for chunk in chunks)
