from __future__ import annotations

import math

import pytest

from app.core import ollama_client


@pytest.mark.asyncio
async def test_generate_embedding_returns_unit_vector(monkeypatch) -> None:
    async def fake_embeddings(**_kwargs):
        return {"embedding": [3.0, 4.0]}

    monkeypatch.setattr(ollama_client.client, "embeddings", fake_embeddings)

    embedding = await ollama_client.generate_embedding("test")

    assert embedding == pytest.approx([0.6, 0.8])
    assert math.sqrt(sum(value * value for value in embedding)) == pytest.approx(1.0)
