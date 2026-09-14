import math
import os

import httpx
import ollama
from ollama import AsyncClient

from app.core.exceptions import (
    AIModelOfflineException,
    EmptyEmbeddingError,
    InvalidResponseError,
    ModelNotFoundError,
    RequestTimeoutError,
)


client = AsyncClient()
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_EMBED_BATCH_SIZE = max(1, int(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "32")))


def _normalize_embedding(content: object) -> list[float]:
    if not isinstance(content, list) or not content:
        raise EmptyEmbeddingError("Embedding rỗng")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in content
    ):
        raise InvalidResponseError("Response không hợp lệ")
    norm = math.sqrt(sum(float(value) ** 2 for value in content))
    if norm == 0:
        raise EmptyEmbeddingError("Embedding có norm bằng 0")
    return [float(value) / norm for value in content]


def _raise_embedding_response_error(exc: ollama.ResponseError) -> None:
    if exc.status_code == 404:
        raise ModelNotFoundError(
            f"Model '{OLLAMA_EMBED_MODEL}' không tồn tại. "
            f"Vui lòng chạy: ollama pull {OLLAMA_EMBED_MODEL}"
        ) from exc
    raise InvalidResponseError("Response không hợp lệ") from exc


async def chat() -> None:
    """Check whether the configured Ollama server is reachable."""
    try:
        await client.list()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise AIModelOfflineException(
            "Chưa mở Ollama hoặc mất kết nối server"
        ) from exc
    except ollama.ResponseError as exc:
        raise AIModelOfflineException("Ollama phản hồi lỗi") from exc
    except Exception as exc:
        raise AIModelOfflineException(
            "Lỗi không xác định khi kết nối Ollama"
        ) from exc


async def generate_embedding(text: str) -> list[float]:
    """Generate one embedding through the current batch-capable API."""
    embeddings = await generate_embeddings([text], batch_size=1)
    return embeddings[0]


async def generate_embeddings(
    texts: list[str],
    batch_size: int | None = None,
) -> list[list[float]]:
    """Generate normalized embeddings in model-level batches."""
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise EmptyEmbeddingError("Không thể embedding nội dung rỗng")

    size = batch_size or OLLAMA_EMBED_BATCH_SIZE
    if size <= 0:
        raise ValueError("batch_size phải lớn hơn 0")
    output: list[list[float]] = []

    for start in range(0, len(texts), size):
        batch = texts[start : start + size]
        try:
            embed_method = getattr(client, "embed", None)
            if callable(embed_method):
                response = await embed_method(model=OLLAMA_EMBED_MODEL, input=batch)
                raw_embeddings = (
                    response.get("embeddings")
                    if isinstance(response, dict)
                    else getattr(response, "embeddings", None)
                )
            else:
                raw_embeddings = []
                for text in batch:
                    response = await client.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text)
                    raw_embeddings.append(
                        response.get("embedding")
                        if isinstance(response, dict)
                        else getattr(response, "embedding", None)
                    )
        except ollama.ResponseError as exc:
            _raise_embedding_response_error(exc)
        except httpx.ConnectError as exc:
            raise AIModelOfflineException("Ollama ngắt kết nối") from exc
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError("Yêu cầu sinh embedding batch hết thời gian chờ") from exc

        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(batch):
            raise InvalidResponseError("Số embedding trả về không khớp batch đầu vào")
        output.extend(_normalize_embedding(embedding) for embedding in raw_embeddings)

    return output


async def generate_chat(prompt: str) -> str:
    """Generate a deterministic RAG answer with the configured chat model."""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = await client.chat(
            model=OLLAMA_CHAT_MODEL,
            messages=messages,
            options={"temperature": 0.0},
        )
    except ollama.ResponseError as exc:
        if exc.status_code == 404:
            raise ModelNotFoundError(
                f"Model '{OLLAMA_CHAT_MODEL}' không tồn tại. "
                f"Vui lòng chạy: ollama pull {OLLAMA_CHAT_MODEL}"
            ) from exc
        raise InvalidResponseError("Response không hợp lệ") from exc
    except httpx.ConnectError as exc:
        raise AIModelOfflineException("Ollama mất kết nối") from exc
    except httpx.TimeoutException as exc:
        raise RequestTimeoutError("Yêu cầu hết thời gian chờ") from exc

    if isinstance(response, dict):
        message = response.get("message")
    else:
        message = getattr(response, "message", None)

    if not message:
        raise InvalidResponseError("Response không hợp lệ")

    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", None)

    if not isinstance(content, str) or not content.strip():
        raise InvalidResponseError("Response không hợp lệ")

    return content
