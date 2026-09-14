"""OCR utilities with reading-order grouping, confidence and persistent cache."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile


logger = logging.getLogger("ocr.utils")
OCR_CACHE_VERSION = "2"


@dataclass
class OCRRegion:
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float


@dataclass
class OCRResult:
    text: str
    regions: list[OCRRegion]
    engine: str = ""
    confidence: float = 0.0
    cached: bool = False


def _empty_result() -> OCRResult:
    return OCRResult(text="", regions=[])


def _cache_key(pil_image, engine_name: str) -> str:
    normalized = pil_image.convert("RGB")
    digest = hashlib.sha256()
    digest.update(OCR_CACHE_VERSION.encode("ascii"))
    digest.update(engine_name.encode("utf-8"))
    digest.update(f"{normalized.width}x{normalized.height}".encode("ascii"))
    digest.update(normalized.tobytes())
    return digest.hexdigest()


def _cache_path(key: str) -> Path | None:
    if os.getenv("OCR_CACHE_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return None
    root = Path(os.getenv("OCR_CACHE_DIR", "storage/ocr_cache"))
    return root / key[:2] / f"{key}.json"


def _load_cache(path: Path | None) -> OCRResult | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        regions = [
            OCRRegion(
                text=str(item["text"]),
                bbox=tuple(float(value) for value in item["bbox"]),
                confidence=float(item["confidence"]),
            )
            for item in payload.get("regions", [])
        ]
        return OCRResult(
            text=str(payload.get("text", "")),
            regions=regions,
            engine=str(payload.get("engine", "")),
            confidence=float(payload.get("confidence", 0.0)),
            cached=True,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.debug("Bỏ qua OCR cache lỗi %s: %s", path, exc)
        return None


def _save_cache(path: Path | None, result: OCRResult) -> None:
    if path is None:
        return
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": OCR_CACHE_VERSION,
            "text": result.text,
            "engine": result.engine,
            "confidence": result.confidence,
            "regions": [asdict(region) for region in result.regions],
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    except OSError as exc:
        logger.debug("Không thể ghi OCR cache %s: %s", path, exc)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _group_words_into_regions(words: list[dict]) -> list[OCRRegion]:
    clean_words = [word for word in words if str(word.get("text", "")).strip()]
    if not clean_words:
        return []
    clean_words.sort(key=lambda word: (float(word.get("top", 0)), float(word.get("x0", 0))))
    heights = sorted(
        max(1.0, float(word.get("bottom", 0)) - float(word.get("top", 0)))
        for word in clean_words
    )
    median_height = heights[len(heights) // 2]
    tolerance = max(3.0, median_height * 0.55)
    lines: list[list[dict]] = []
    line_centers: list[float] = []

    for word in clean_words:
        center = (float(word.get("top", 0)) + float(word.get("bottom", 0))) / 2
        match_index = next(
            (index for index, line_center in enumerate(line_centers) if abs(center - line_center) <= tolerance),
            None,
        )
        if match_index is None:
            lines.append([word])
            line_centers.append(center)
        else:
            lines[match_index].append(word)
            line_centers[match_index] = sum(
                (float(item.get("top", 0)) + float(item.get("bottom", 0))) / 2
                for item in lines[match_index]
            ) / len(lines[match_index])

    ordered = sorted(zip(line_centers, lines), key=lambda item: item[0])
    regions: list[OCRRegion] = []
    for _, line_words in ordered:
        line_words.sort(key=lambda word: float(word.get("x0", 0)))
        horizontal_groups: list[list[dict]] = []
        for word in line_words:
            if not horizontal_groups:
                horizontal_groups.append([word])
                continue
            previous_x1 = max(float(item.get("x1", 0)) for item in horizontal_groups[-1])
            gap = float(word.get("x0", 0)) - previous_x1
            if gap > max(40.0, median_height * 4):
                horizontal_groups.append([word])
            else:
                horizontal_groups[-1].append(word)

        for group in horizontal_groups:
            confidences = [float(word.get("confidence", 1.0)) for word in group]
            regions.append(OCRRegion(
                text=" ".join(str(word["text"]).strip() for word in group),
                bbox=(
                    min(float(word.get("x0", 0)) for word in group),
                    min(float(word.get("top", 0)) for word in group),
                    max(float(word.get("x1", 0)) for word in group),
                    max(float(word.get("bottom", 0)) for word in group),
                ),
                confidence=sum(confidences) / len(confidences),
            ))
    return _order_regions_by_columns(regions)


def _order_regions_by_columns(regions: list[OCRRegion]) -> list[OCRRegion]:
    """Prefer column-major reading order when two stable x-start groups exist."""
    if len(regions) < 4:
        return sorted(regions, key=lambda region: (region.bbox[1], region.bbox[0]))
    page_left = min(region.bbox[0] for region in regions)
    page_right = max(region.bbox[2] for region in regions)
    page_width = max(1.0, page_right - page_left)
    sorted_starts = sorted((region.bbox[0], index) for index, region in enumerate(regions))
    gaps = [
        (sorted_starts[index + 1][0] - sorted_starts[index][0], index)
        for index in range(len(sorted_starts) - 1)
    ]
    largest_gap, gap_index = max(gaps, default=(0.0, 0))
    left_indexes = {index for _, index in sorted_starts[: gap_index + 1]}
    right_indexes = {index for _, index in sorted_starts[gap_index + 1 :]}
    if (
        largest_gap < page_width * 0.25
        or len(left_indexes) < 2
        or len(right_indexes) < 2
    ):
        return sorted(regions, key=lambda region: (region.bbox[1], region.bbox[0]))

    divider = (sorted_starts[gap_index][0] + sorted_starts[gap_index + 1][0]) / 2
    spanning = [
        region for region in regions
        if region.bbox[0] < divider < region.bbox[2]
    ]
    left = [
        region for region in regions
        if region not in spanning and (region.bbox[0] + region.bbox[2]) / 2 < divider
    ]
    right = [region for region in regions if region not in spanning and region not in left]
    if len(left) < 2 or len(right) < 2:
        return sorted(regions, key=lambda region: (region.bbox[1], region.bbox[0]))

    column_top = min(region.bbox[1] for region in [*left, *right])
    leading = sorted(
        [region for region in spanning if region.bbox[1] <= column_top],
        key=lambda region: (region.bbox[1], region.bbox[0]),
    )
    trailing = sorted(
        [region for region in spanning if region not in leading],
        key=lambda region: (region.bbox[1], region.bbox[0]),
    )
    return [
        *leading,
        *sorted(left, key=lambda region: (region.bbox[1], region.bbox[0])),
        *sorted(right, key=lambda region: (region.bbox[1], region.bbox[0])),
        *trailing,
    ]


def ocr_image_to_result(pil_image) -> OCRResult:
    """OCR an image once and return text, regions, coordinates and confidence."""
    try:
        from app.services.ocr.factory import OCRFactory

        engine = OCRFactory.get_engine()
        cache_path = _cache_path(_cache_key(pil_image, engine.name))
        cached = _load_cache(cache_path)
        if cached is not None:
            return cached

        words = engine.extract_words(pil_image, scale=1.0)
        regions = _group_words_into_regions(words)
        if not regions:
            result = OCRResult(text="", regions=[], engine=engine.name)
        else:
            result = OCRResult(
                text="\n".join(region.text for region in regions),
                regions=regions,
                engine=engine.name,
                confidence=sum(region.confidence for region in regions) / len(regions),
            )
        _save_cache(cache_path, result)
        return result
    except ImportError:
        logger.debug("OCR engine không khả dụng")
        return _empty_result()
    except Exception as exc:
        logger.warning("OCR lỗi: %s", exc)
        return _empty_result()


def ocr_image_to_text(pil_image) -> str:
    """Backward-compatible text-only OCR API."""
    return ocr_image_to_result(pil_image).text.replace("\n", "\n> ")


def ocr_image_file_to_result(image_path: str) -> OCRResult:
    try:
        from PIL import Image as PILImage

        with PILImage.open(image_path) as image:
            return ocr_image_to_result(image.convert("RGB"))
    except Exception as exc:
        logger.warning("Không thể mở ảnh %s: %s", image_path, exc)
        return _empty_result()


def ocr_image_file_to_text(image_path: str) -> str:
    """Backward-compatible text-only OCR API for an image path."""
    return ocr_image_file_to_result(image_path).text.replace("\n", "\n> ")
