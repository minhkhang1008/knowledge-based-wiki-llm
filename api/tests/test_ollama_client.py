from __future__ import annotations

import asyncio
import math

import pytest

from app.core import ollama_client


def test_generate_embedding_returns_unit_vector(monkeypatch) -> None:
    async def fake_embed(**_kwargs):
        return {"embeddings": [[3.0, 4.0]]}

    monkeypatch.setattr(ollama_client.client, "embed", fake_embed)

    embedding = asyncio.run(ollama_client.generate_embedding("test"))

    assert embedding == pytest.approx([0.6, 0.8])
    assert math.sqrt(sum(value * value for value in embedding)) == pytest.approx(1.0)


def test_generate_embeddings_batches_and_normalizes(monkeypatch) -> None:
    calls: list[list[str]] = []

    async def fake_embed(**kwargs):
        batch = kwargs["input"]
        calls.append(batch)
        return {"embeddings": [[3.0, 4.0] for _ in batch]}

    monkeypatch.setattr(ollama_client.client, "embed", fake_embed)

    embeddings = asyncio.run(
        ollama_client.generate_embeddings(["a", "b", "c"], batch_size=2)
    )

    assert calls == [["a", "b"], ["c"]]
    assert all(embedding == pytest.approx([0.6, 0.8]) for embedding in embeddings)
