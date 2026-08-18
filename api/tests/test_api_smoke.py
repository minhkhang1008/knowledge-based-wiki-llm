from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine


def test_ui_facing_api_contract_is_registered(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "knowledge_base.db"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    monkeypatch.setenv(
        "CHROMA_PERSIST_PATH",
        str(tmp_path / "chroma"),
    )

    import app.core.database as database
    from app.main import app

    monkeypatch.setattr(
        database,
        "engine",
        create_async_engine(f"sqlite+aiosqlite:///{database_path}"),
    )

    paths = set(app.openapi()["paths"])
    assert {
        "/api/articles",
        "/api/articles/{article_id}",
        "/api/qa/ask",
        "/api/search",
        "/api/stats",
        "/api/v1/articles/upload",
        "/api/v1/articles/upload-presentation",
        "/api/v1/articles/supported-formats",
    } <= paths

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"articles", "qa_logs"} <= tables


def test_supported_formats_only_include_ready_ingestion_paths() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/articles/supported-formats")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["extensions"] == [".docx", ".pptx", ".xlsm", ".xlsx"]
    assert payload["max_upload_size_mb"] > 0
