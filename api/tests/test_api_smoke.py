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
        "/api/v1/articles/{document_id}/assets/{asset_path}",
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
    assert payload["extensions"] == [
        ".bmp",
        ".docx",
        ".gif",
        ".jpeg",
        ".jpg",
        ".pdf",
        ".png",
        ".pptx",
        ".tif",
        ".tiff",
        ".webp",
        ".xlsm",
        ".xlsx",
    ]
    assert payload["max_upload_size_mb"] > 0


def test_document_asset_endpoint_serves_only_images_below_document_root(
    tmp_path,
    monkeypatch,
) -> None:
    import app.api.v1.articles as articles_api
    from app.main import app

    document_id = "a" * 64
    document_dir = tmp_path / document_id / "images"
    document_dir.mkdir(parents=True)
    image = document_dir / "diagram.png"
    image.write_bytes(b"fake-png")
    (document_dir / "notes.txt").write_text("private", encoding="utf-8")
    (tmp_path / "secret.png").write_bytes(b"outside")
    monkeypatch.setattr(articles_api, "EXTRACTED_DATA_DIR", tmp_path.resolve())

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/articles/{document_id}/assets/images/diagram.png"
        )
        text_response = client.get(
            f"/api/v1/articles/{document_id}/assets/images/notes.txt"
        )
        traversal_response = client.get(
            f"/api/v1/articles/{document_id}/assets/%2E%2E/secret.png"
        )

    assert response.status_code == 200
    assert response.content == b"fake-png"
    assert response.headers["cache-control"] == "private, max-age=3600"
    assert text_response.status_code == 404
    assert traversal_response.status_code == 404
