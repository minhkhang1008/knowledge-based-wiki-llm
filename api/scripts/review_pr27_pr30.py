#!/usr/bin/env python3
"""
Smoke test cho PR #27 và PR #30.

Cách chạy từ thư mục gốc repository:
    python scripts/review_pr27_pr30.py
    python scripts/review_pr27_pr30.py --only pr27
    python scripts/review_pr27_pr30.py --only pr30

Script không cần pytest. Nó chỉ dùng các dependency vốn có của backend.
Exit code = 0 khi tất cả test pass, = 1 khi còn lỗi.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Awaitable, Callable


def find_repo_root() -> Path:
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parents[1],
        Path(__file__).resolve().parent,
    ]
    for candidate in candidates:
        if (candidate / "api" / "app").is_dir():
            return candidate
    raise RuntimeError(
        "Không tìm thấy thư mục api/app. "
        "Hãy đặt script trong <repo>/scripts/ và chạy từ thư mục gốc repo."
    )


ROOT = find_repo_root()
API_DIR = ROOT / "api"
sys.path.insert(0, str(API_DIR))

# DATABASE_URL phải được đặt trước khi import app.core.database.
_fd, _db_name = tempfile.mkstemp(prefix="pr27_pr30_", suffix=".db")
os.close(_fd)
DB_PATH = Path(_db_name)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"


class ReviewRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    async def run(
        self,
        group: str,
        name: str,
        test: Callable[[], Awaitable[None]],
    ) -> None:
        try:
            await test()
        except Exception as exc:
            self.failed += 1
            print(f"[FAIL] {group} | {name}")
            print(f"       {type(exc).__name__}: {exc}")
        else:
            self.passed += 1
            print(f"[PASS] {group} | {name}")

    def summary(self) -> int:
        total = self.passed + self.failed
        print("\n" + "=" * 64)
        print(f"Kết quả: {self.passed}/{total} pass, {self.failed} fail")
        if self.failed:
            print("PR vẫn cần sửa trước khi merge.")
            return 1
        print("Các kiểm tra trong script đều pass.")
        return 0


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def test_pr27_database_lifecycle_declared() -> None:
    main_file = API_DIR / "app" / "main.py"
    source = main_file.read_text(encoding="utf-8")

    require(
        "init_db" in source,
        "main.py chưa gọi/import init_db() khi backend khởi động.",
    )
    require(
        "close_db" in source,
        "main.py chưa gọi/import close_db() khi backend dừng.",
    )
    require(
        "lifespan" in source or "on_event" in source,
        "main.py chưa nối init_db()/close_db() vào lifespan hoặc startup/shutdown event.",
    )


async def test_pr27_init_and_log_persist() -> None:
    database = importlib.import_module("app.core.database")
    qa_repo = importlib.import_module("app.repositories.qa_log_repository")
    qa_model = importlib.import_module("app.models.qa_log")

    from sqlalchemy import select

    await database.init_db()

    async with database.AsyncSessionLocal() as session:
        await qa_repo.log_qa_interaction(
            session,
            "Nhân viên có bao nhiêu ngày phép?",
            "Nhân viên có 12 ngày phép.",
            [{"article_id": "a1", "source_file": "hr.pdf"}],
        )

    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(qa_model.QALog))
        row = result.scalar_one_or_none()

    require(row is not None, "Không đọc lại được QA log sau khi commit.")
    require(row.question == "Nhân viên có bao nhiêu ngày phép?", "question lưu sai.")
    require(row.answer == "Nhân viên có 12 ngày phép.", "answer lưu sai.")
    require(isinstance(row.sources, list), "sources phải được lưu dưới dạng JSON list.")


async def test_pr27_repository_rolls_back_and_reraises() -> None:
    qa_repo = importlib.import_module("app.repositories.qa_log_repository")

    class FailingSession:
        def __init__(self) -> None:
            self.rollback_called = False
            self.commit_called = False

        async def execute(self, statement):
            raise RuntimeError("forced database failure")

        async def commit(self) -> None:
            self.commit_called = True

        async def rollback(self) -> None:
            self.rollback_called = True

    session = FailingSession()

    try:
        await qa_repo.log_qa_interaction(
            session,
            "question",
            "answer",
            [],
        )
    except RuntimeError as exc:
        require(str(exc) == "forced database failure", "Repository đổi exception gốc.")
    else:
        raise AssertionError("Repository đã nuốt exception thay vì raise lại.")

    require(session.rollback_called, "Repository chưa rollback khi ghi log thất bại.")
    require(not session.commit_called, "Không được commit sau khi execute thất bại.")


async def test_pr27_upsert_returns_article() -> None:
    """Kiểm tra thêm vì PR #27 đang sửa cả Article Repository."""
    database = importlib.import_module("app.core.database")
    article_repo = importlib.import_module("app.repositories.article_repository")

    await database.init_db()

    payload = {
        "document_id": "doc-review-1",
        "title": "Review article",
        "content": "Nội dung kiểm tra",
        "source_file": "review.pdf",
    }

    async with database.AsyncSessionLocal() as session:
        article = await article_repo.upsert_article_by_document_id(session, payload)

    require(
        article is not None,
        "upsert_article_by_document_id() commit xong nhưng không return Article.",
    )
    require(
        getattr(article, "document_id", None) == "doc-review-1",
        "Article trả về không đúng document_id.",
    )


def get_expected_schema_class(module_name: str, class_name: str):
    module = importlib.import_module(f"app.schemas.{module_name}")
    cls = getattr(module, class_name, None)
    require(
        cls is not None,
        f"{module_name}.py phải khai báo class {class_name} đúng PascalCase.",
    )
    return cls


async def test_pr30_schema_class_names() -> None:
    expected = [
        ("ErrorResponse", "ErrorResponse"),
        ("SourceResponse", "SourceResponse"),
        ("ChatMessage", "ChatMessage"),
        ("AskRequest", "AskRequest"),
        ("AskResponse", "AskResponse"),
        ("SearchData", "SearchData"),
        ("SearchResponse", "SearchResponse"),
    ]
    for module_name, class_name in expected:
        get_expected_schema_class(module_name, class_name)


async def make_api_test_client():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient

    qa_module = importlib.import_module("app.api.v1.qa")
    search_module = importlib.import_module("app.api.v1.search")
    exceptions = importlib.import_module("app.core.exceptions")

    app = FastAPI()
    app.include_router(qa_module.router)
    app.include_router(search_module.router)

    @app.exception_handler(exceptions.AIModelOfflineException)
    async def offline_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "data": None,
                "message": "Hệ thống AI đang ngoại tuyến",
                "error": {
                    "code": "AI_ENGINE_OFFLINE",
                    "detail": str(exc),
                },
            },
        )

    async def fake_db():
        yield object()

    app.dependency_overrides[qa_module.get_db] = fake_db
    client = TestClient(app, raise_server_exceptions=False)
    return client, qa_module, search_module, exceptions


async def test_pr30_qa_success_allows_none_reason() -> None:
    client, qa_module, _, _ = await make_api_test_client()
    old_pipeline = qa_module.process_rag_pipeline
    old_logger = qa_module.log_qa_interaction

    async def fake_pipeline(question, chat_history=None):
        return {
            "answer": "Có 12 ngày phép.",
            "sources": [{"article_id": "a1", "source_file": "hr.pdf"}],
            "no_answer_reason": None,
        }

    async def fake_logger(session, question, answer, sources):
        return None

    qa_module.process_rag_pipeline = fake_pipeline
    qa_module.log_qa_interaction = fake_logger
    try:
        response = client.post(
            "/api/qa/ask",
            json={"question": "Có bao nhiêu ngày phép?", "chat_history": []},
        )
    finally:
        client.close()
        qa_module.process_rag_pipeline = old_pipeline
        qa_module.log_qa_interaction = old_logger

    require(response.status_code == 200, f"Expected 200, got {response.status_code}.")
    payload = response.json()
    require(payload.get("success") is True, f"QA success bị trả thành lỗi: {payload}")
    require(payload["data"]["no_answer_reason"] is None, "no_answer_reason phải nhận None.")
    require(payload.get("error") is None, "QA success phải có error=None.")


async def test_pr30_qa_no_context_is_success() -> None:
    client, qa_module, _, _ = await make_api_test_client()
    old_pipeline = qa_module.process_rag_pipeline
    old_logger = qa_module.log_qa_interaction

    async def fake_pipeline(question, chat_history=None):
        return {
            "answer": "Tôi không tìm thấy thông tin này trong tài liệu.",
            "sources": [],
            "no_answer_reason": "insufficient_context",
        }

    async def fake_logger(session, question, answer, sources):
        return None

    qa_module.process_rag_pipeline = fake_pipeline
    qa_module.log_qa_interaction = fake_logger
    try:
        response = client.post(
            "/api/qa/ask",
            json={"question": "Câu hỏi ngoài tài liệu", "chat_history": []},
        )
    finally:
        client.close()
        qa_module.process_rag_pipeline = old_pipeline
        qa_module.log_qa_interaction = old_logger

    payload = response.json()
    require(response.status_code == 200, f"Expected 200, got {response.status_code}.")
    require(payload.get("success") is True, "Không có context vẫn phải success=True.")
    require(payload["data"]["sources"] == [], "Không có context thì sources phải rỗng.")
    require(payload.get("error") is None, "Không có context thì error phải là None.")


async def test_pr30_qa_offline_returns_503() -> None:
    client, qa_module, _, exceptions = await make_api_test_client()
    old_pipeline = qa_module.process_rag_pipeline

    async def offline_pipeline(question, chat_history=None):
        raise exceptions.AIModelOfflineException("Ollama offline")

    qa_module.process_rag_pipeline = offline_pipeline
    try:
        response = client.post(
            "/api/qa/ask",
            json={"question": "Kiểm tra hệ thống AI", "chat_history": []},
        )
    finally:
        client.close()
        qa_module.process_rag_pipeline = old_pipeline

    require(
        response.status_code == 503,
        f"Ollama offline phải trả HTTP 503, hiện trả {response.status_code}: {response.text}",
    )


async def test_pr30_qa_unexpected_error_returns_500() -> None:
    client, qa_module, _, _ = await make_api_test_client()
    old_pipeline = qa_module.process_rag_pipeline

    async def broken_pipeline(question, chat_history=None):
        raise RuntimeError("forced failure")

    qa_module.process_rag_pipeline = broken_pipeline
    try:
        response = client.post(
            "/api/qa/ask",
            json={"question": "Kiểm tra lỗi hệ thống", "chat_history": []},
        )
    finally:
        client.close()
        qa_module.process_rag_pipeline = old_pipeline

    require(
        response.status_code == 500,
        f"Lỗi không dự kiến phải trả HTTP 500, hiện trả {response.status_code}.",
    )


async def test_pr30_chat_history_validation() -> None:
    client, qa_module, _, _ = await make_api_test_client()
    old_pipeline = qa_module.process_rag_pipeline
    old_logger = qa_module.log_qa_interaction

    async def fake_pipeline(question, chat_history=None):
        return {
            "answer": "ok",
            "sources": [],
            "no_answer_reason": None,
        }

    async def fake_logger(session, question, answer, sources):
        return None

    qa_module.process_rag_pipeline = fake_pipeline
    qa_module.log_qa_interaction = fake_logger
    try:
        response = client.post(
            "/api/qa/ask",
            json={
                "question": "Kiểm tra chat history",
                "chat_history": [{"foo": "bar"}],
            },
        )
    finally:
        client.close()
        qa_module.process_rag_pipeline = old_pipeline
        qa_module.log_qa_interaction = old_logger

    require(
        response.status_code == 422,
        "chat_history phải là list[ChatMessage]; phần tử thiếu role/content phải trả 422.",
    )


async def test_pr30_search_response_contract() -> None:
    client, _, search_module, _ = await make_api_test_client()
    old_search = search_module.semantic_search_logic

    async def fake_search(query):
        return [
            {
                "text": "Nhân viên có 12 ngày phép.",
                "article_id": "a1",
                "source_file": "hr.pdf",
                "page_number": 3,
                "distance": 0.1,
            }
        ]

    search_module.semantic_search_logic = fake_search
    try:
        response = client.post("/api/search", json={"query": "ngày phép"})
    finally:
        client.close()
        search_module.semantic_search_logic = old_search

    require(response.status_code == 200, f"Expected 200, got {response.status_code}.")
    payload = response.json()
    require(isinstance(payload.get("data"), dict), "SearchResponse.data phải là object.")
    require("results" in payload["data"], "SearchResponse phải dùng data.results.")
    result = payload["data"]["results"][0]
    require(result.get("source_file") == "hr.pdf", "source_file đang bị sai tên hoặc bị mất.")


async def test_pr30_search_offline_returns_503() -> None:
    client, _, search_module, exceptions = await make_api_test_client()
    old_search = search_module.semantic_search_logic

    async def offline_search(query):
        raise exceptions.AIModelOfflineException("Ollama offline")

    search_module.semantic_search_logic = offline_search
    try:
        response = client.post("/api/search", json={"query": "ngày phép"})
    finally:
        client.close()
        search_module.semantic_search_logic = old_search

    require(
        response.status_code == 503,
        f"Ollama offline phải trả HTTP 503, hiện trả {response.status_code}: {response.text}",
    )


async def test_pr30_request_validation_returns_422() -> None:
    client, _, _, _ = await make_api_test_client()
    try:
        qa_response = client.post(
            "/api/qa/ask",
            json={"question": "abc", "chat_history": []},
        )
        search_response = client.post("/api/search", json={"query": "a"})
    finally:
        client.close()

    require(qa_response.status_code == 422, "AskRequest.question < 5 phải trả 422.")
    require(search_response.status_code == 422, "Search query quá ngắn phải trả 422.")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=["all", "pr27", "pr30"],
        default="all",
        help="Chỉ chạy test của một PR.",
    )
    args = parser.parse_args()

    runner = ReviewRunner()

    try:
        if args.only in {"all", "pr27"}:
            await runner.run(
                "PR #27",
                "main.py nối init_db/close_db vào lifecycle",
                test_pr27_database_lifecycle_declared,
            )
            await runner.run(
                "PR #27",
                "init_db + QA log commit và đọc lại được",
                test_pr27_init_and_log_persist,
            )
            await runner.run(
                "PR #27",
                "QA repository rollback và raise lại exception",
                test_pr27_repository_rolls_back_and_reraises,
            )
            await runner.run(
                "PR #27 extra",
                "Article upsert phải return Article",
                test_pr27_upsert_returns_article,
            )

        if args.only in {"all", "pr30"}:
            await runner.run(
                "PR #30",
                "Tên schema đúng PascalCase",
                test_pr30_schema_class_names,
            )
            await runner.run(
                "PR #30",
                "QA success cho phép no_answer_reason=None",
                test_pr30_qa_success_allows_none_reason,
            )
            await runner.run(
                "PR #30",
                "Không có context vẫn HTTP 200 và success=True",
                test_pr30_qa_no_context_is_success,
            )
            await runner.run(
                "PR #30",
                "QA Ollama offline trả HTTP 503",
                test_pr30_qa_offline_returns_503,
            )
            await runner.run(
                "PR #30",
                "QA lỗi không dự kiến trả HTTP 500",
                test_pr30_qa_unexpected_error_returns_500,
            )
            await runner.run(
                "PR #30",
                "chat_history validate bằng ChatMessage",
                test_pr30_chat_history_validation,
            )
            await runner.run(
                "PR #30",
                "SearchResponse dùng data.results và giữ source_file",
                test_pr30_search_response_contract,
            )
            await runner.run(
                "PR #30",
                "Search Ollama offline trả HTTP 503",
                test_pr30_search_offline_returns_503,
            )
            await runner.run(
                "PR #30",
                "Request sai trả HTTP 422",
                test_pr30_request_validation_returns_422,
            )

        return runner.summary()
    finally:
        try:
            database = sys.modules.get("app.core.database")
            if database is not None:
                await database.close_db()
        finally:
            try:
                DB_PATH.unlink(missing_ok=True)
            except PermissionError:
                # Windows có thể giữ file SQLite thêm một lúc.
                pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
