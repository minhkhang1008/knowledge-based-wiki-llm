"""Optional, cached local vision captioning for images that OCR cannot index."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path


logger = logging.getLogger("document_parser.vision_caption")
PROMPT_VERSION = "1"


def generate_image_caption(image_path: str | Path) -> tuple[str, str]:
    """Return ``(caption, model)``; disabled by default and failure-tolerant."""
    if os.getenv("IMAGE_VISION_CAPTION_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return "", ""

    path = Path(image_path)
    model = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")
    try:
        digest = hashlib.sha256()
        digest.update(PROMPT_VERSION.encode("ascii"))
        digest.update(model.encode("utf-8"))
        digest.update(path.read_bytes())
        key = digest.hexdigest()
        cache_path = Path(os.getenv("VISION_CACHE_DIR", "storage/vision_cache")) / key[:2] / f"{key}.txt"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8").strip(), model

        import ollama

        response = ollama.Client().chat(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    "Mô tả ngắn gọn, chính xác nội dung và các quan hệ quan trọng "
                    "trong ảnh này bằng tiếng Việt. Không suy đoán thông tin không thấy."
                ),
                "images": [str(path)],
            }],
            options={"temperature": 0.0},
        )
        message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
        caption = (
            message.get("content", "")
            if isinstance(message, dict)
            else getattr(message, "content", "")
        )
        caption = caption.strip() if isinstance(caption, str) else ""
        if caption:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(caption, encoding="utf-8")
        return caption, model
    except Exception as exc:
        logger.warning("Không thể sinh vision caption cho %s: %s", path, exc)
        return "", model
