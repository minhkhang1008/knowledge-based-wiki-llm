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
    """Generate and L2-normalize an embedding for stable distance scores."""
    try:
        response = await client.embeddings(
            model=OLLAMA_EMBED_MODEL,
            prompt=text,
        )
    except ollama.ResponseError as exc:
        if exc.status_code == 404:
            raise ModelNotFoundError(
                f"Model '{OLLAMA_EMBED_MODEL}' không tồn tại. "
                f"Vui lòng chạy: ollama pull {OLLAMA_EMBED_MODEL}"
            ) from exc
        raise InvalidResponseError("Response không hợp lệ") from exc
    except httpx.ConnectError as exc:
        raise AIModelOfflineException("Ollama ngắt kết nối") from exc
    except httpx.TimeoutException as exc:
        raise RequestTimeoutError(
            "Yêu cầu sinh embedding text hết thời gian chờ"
        ) from exc

    if isinstance(response, dict):
        content = response.get("embedding")
    else:
        content = getattr(response, "embedding", None)

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
