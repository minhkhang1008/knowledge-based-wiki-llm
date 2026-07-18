import os
import re
import logging
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from app.services.document_parser.converter_registry import register

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pdf_converter")

class BlockType(Enum):
    HEADER_1 = "h1"
    HEADER_2 = "h2"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    def contains_point(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

@dataclass
class DocumentBlock:
    block_type: BlockType
    bbox: BoundingBox
    content: str
    confidence: float = 1.0
    ocr_text: str = ""  # OCR text từ ảnh (chỉ dùng với BlockType.IMAGE)

@dataclass
class TextLine:
    text: str
    bbox: BoundingBox
    font_size: float
    words: List[dict]

class MuPDFTextExtractor:
    """
    Dùng pymupdf (fitz) để extract text với unicode mapping tốt hơn pdfplumber.
    pymupdf xử lý đúng °C, kΩ, µF, –, ≈ mà không cần regex cleanup thủ công.
    Được dùng làm primary text engine, pdfplumber giữ vai trò detect table/image.
    """

    @staticmethod
    def available() -> bool:
        try:
            import fitz  # noqa
            return True
        except ImportError:
            return False

    @staticmethod
    def get_page_blocks(fitz_page) -> List[dict]:
        """
        Trả về list blocks từ pymupdf với format chuẩn hóa:
        {"text": str, "y0": float, "y1": float, "x0": float, "x1": float,
         "font_size": float, "bold": bool}
        """
        blocks = []
        raw_blocks = fitz_page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for b in raw_blocks:
            if b.get("type") != 0:  # 0 = text block
                continue
            for line in b.get("lines", []):
                line_text = ""
                max_size = 0.0
                is_bold = False
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    size = float(span.get("size", 0))
                    if size > max_size:
                        max_size = size
                    flags = span.get("flags", 0)
                    if flags & 16:  # bold flag
                        is_bold = True
                line_text = line_text.strip()
                if not line_text:
                    continue
                bbox = line.get("bbox", (0, 0, 0, 0))
                blocks.append({
                    "text": line_text,
                    "x0": bbox[0], "y0": bbox[1],
                    "x1": bbox[2], "y1": bbox[3],
                    "font_size": max_size,
                    "bold": is_bold,
                })
        return blocks

    @staticmethod
    def compute_font_stats_from_doc(fitz_doc, max_pages: int = 15) -> dict:
        """Tính most_used_font_size và max_font_size từ pymupdf document."""
        size_counter: Counter = Counter()
        max_size = 0.0
        for page in list(fitz_doc)[:max_pages]:
            for b in page.get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        size = float(span.get("size", 0))
                        if size > 0:
                            size_counter[round(size * 2) / 2] += 1
                            if size > max_size:
                                max_size = size
        most_used = size_counter.most_common(1)[0][0] if size_counter else 10.0
        return {"most_used": most_used, "max": max_size or most_used}




class PDFTextCleaner:
    # Map (cid:x) → ký tự Unicode tương ứng cho các font phổ biến
    _CID_MAP = {
        "1": "°", "2": "±", "3": "−", "4": "×", "5": "µ",
        "6": "·", "7": "→", "8": "←", "9": "↑", "10": "↓",
        "14": "•", "15": "·", "16": "™", "17": "©", "18": "®",
        "25": "°", "30": "Ω", "32": "·",
    }

    @staticmethod
    def clean(text: str) -> str:
        """Làm sạch encoding artifact phổ biến trong cấu trúc nhị phân PDF."""
        if not text:
            return ""

        # Thay thế (cid:x) theo map, còn lại xóa
        def replace_cid(m):
            return PDFTextCleaner._CID_MAP.get(m.group(1), "")
        text = re.sub(r"\(cid:(\d+)\)", replace_cid, text)

        # Ký hiệu điện tử bị encode sai — chỉ convert khi đứng sau số
        # để tránh nhầm với đơn vị kilowatt/megawatt trong tài liệu năng lượng
        text = re.sub(r"(\d)\s*kW(?!\w)", r"\1 kΩ", text)   # 100kW → 100 kΩ (chỉ sau số)
        text = re.sub(r"(\d)\s*MW(?!\w)", r"\1 MΩ", text)   # 10MW → 10 MΩ (chỉ sau số)
        text = re.sub(r"\b(\d+(?:\.\d+)?)\s*W\b", r"\1 Ω", text)
        text = re.sub(r"\b(\d+(?:\.\d+)?)\s*m\s*F\b", r"\1 µF", text)
        text = text.replace("»", "≈").replace("«", "≈")
        # °C: chỉ convert khi C đứng sau số/dấu gạch ngang, không sau chữ cái
        text = re.sub(r"(\d)\s+C\b(?!\w)", r"\1°C", text)     # 25 C → 25°C
        text = re.sub(r"(–\d+)\s*C\b(?!\w)", r"\1°C", text)   # –55 C → –55°C
        text = re.sub(r"\bC\b(?=\s*/\s*W)", "°C", text)        # C/W → °C/W

        return text

class FontStatsAnalyzer:
    """Chuyên trách phân tích đặc trưng font toàn văn bản nhằm thiết lập bộ Heuristic."""
    @staticmethod
    def analyze(pdf, max_sample_pages: int = 15) -> dict:
        size_counter: Counter = Counter()
        font_counter: Counter = Counter()
        bold_font_names = set()
        max_font_size = 0.0
        
        sampled_pages = pdf.pages[:max_sample_pages]
        for page in sampled_pages:
            # Tối ưu: Lấy trực thuộc thuộc tính từ đối tượng thay vì quét sâu glyph phức tạp nếu không cần thiết
            chars = page.chars
            if not chars:
                continue
            for char in chars:
                size = char.get("size")
                fname = char.get("fontname", "")
                if size and float(size) > 0:
                    rounded = round(float(size) * 2) / 2
                    size_counter[rounded] += 1
                    font_counter[fname] += 1
                    if float(size) > max_font_size:
                        max_font_size = float(size)
                    if "bold" in fname.lower() or fname.endswith("-Bold") or fname.endswith("Bold"):
                        bold_font_names.add(fname)
                        
        most_used_size = size_counter.most_common(1)[0][0] if size_counter else 10.0
        most_used_font = font_counter.most_common(1)[0][0] if font_counter else ""
        if max_font_size == 0.0:
            max_font_size = most_used_size
            
        return {
            "most_used_font_size": most_used_size,
            "most_used_font_name": most_used_font,
            "max_font_size": max_font_size,
            "bold_font_names": bold_font_names,
        }

class TableConverter:
    """Chuyên trách chuyển đổi ma trận bảng dữ liệu thô sang định dạng Markdown chuẩn."""
    @staticmethod
    def to_markdown(raw_table: List[List[Optional[str]]]) -> str:
        if not raw_table or not raw_table[0]:
            return ""
            
        def clean_cell(cell: Optional[str]) -> str:
            if cell is None:
                return ""
            return PDFTextCleaner.clean(str(cell).replace("\n", " ").replace("|", "\\|").strip())
            
        headers = [clean_cell(c) for c in raw_table[0]]
        num_cols = len(headers)
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * num_cols) + " |",
        ]
        for row in raw_table[1:]:
            cells = [clean_cell(c) for c in row]
            if len(cells) < num_cols:
                cells += [""] * (num_cols - len(cells))
            lines.append("| " + " | ".join(cells[:num_cols]) + " |")
        return "\n".join(lines)

class TextLineGrouper:
    """Tối ưu hóa thuật toán nhóm từ thành dòng sử dụng cơ chế Sweep-line đơn giản."""
    @staticmethod
    def group(words: List[dict], y_tolerance: float = 3.0) -> List[TextLine]:
        if not words:
            return []
            
        # Sắp xếp theo trục dọc trước
        sorted_words = sorted(words, key=lambda w: float(w["top"]))
        lines: List[List[dict]] = []
        
        for word in sorted_words:
            top = float(word["top"])
            bottom = float(word["bottom"])
            
            placed = False
            # Kiểm tra nhanh dòng cuối cùng hiện tại xem có cùng nằm trên một dòng quét không
            if lines:
                last_line = lines[-1]
                ref_word = last_line[0]
                ref_top = float(ref_word["top"])
                ref_bottom = float(ref_word["bottom"])
                
                # Tính độ giao thoa theo trục Y
                overlap = max(0.0, min(bottom, ref_bottom) - max(top, ref_top))
                min_h = min(bottom - top, ref_bottom - ref_top)
                
                if min_h > 0 and (overlap / min_h) > 0.5:
                    last_line.append(word)
                    placed = True
            
            if not placed:
                lines.append([word])
                
        result: List[TextLine] = []
        for lw in lines:
            sw = sorted(lw, key=lambda w: w["x0"])
            text = " ".join(str(w["text"]) for w in sw).strip()
            if not text:
                continue
                
            result.append(TextLine(
                text=text,
                bbox=BoundingBox(
                    min(w["x0"] for w in sw), min(w["top"] for w in sw),
                    max(w["x1"] for w in sw), max(w["bottom"] for w in sw),
                ),
                font_size=sum(float(w["bottom"]) - float(w["top"]) for w in sw) / len(sw),
                words=sw,
            ))
        return result

class MarkdownCompiler:
    @staticmethod
    def compile(blocks: List[DocumentBlock]) -> str:
        markdown_lines: List[str] = []
        for block in blocks:
            cleaned_content = PDFTextCleaner.clean(block.content.strip())

            # IMAGE không cần content — kiểm tra ocr_text riêng
            if block.block_type == BlockType.IMAGE:
                if block.ocr_text:
                    markdown_lines.append(f'\n<img>\n"""\n{block.ocr_text}\n"""\n')
                elif cleaned_content:
                    markdown_lines.append(f"\n<img> {cleaned_content}\n")
                else:
                    markdown_lines.append("\n<img>\n")
                continue

            if not cleaned_content:
                continue
            if block.block_type == BlockType.HEADER_1:
                markdown_lines.append(f"\n# {cleaned_content}\n")
            elif block.block_type == BlockType.HEADER_2:
                markdown_lines.append(f"\n## {cleaned_content}\n")
            elif block.block_type == BlockType.LIST_ITEM:
                if re.match(r"^[\-\*\•\●]\s+", cleaned_content):
                    markdown_lines.append(f"* {cleaned_content[2:].strip()}\n")
                elif re.match(r"^\d+[\.|\)]", cleaned_content):
                    markdown_lines.append(f"{cleaned_content}\n")
                else:
                    markdown_lines.append(f"* {cleaned_content}\n")
            elif block.block_type == BlockType.TABLE:
                markdown_lines.append(f"\n{cleaned_content}\n")
            else:
                markdown_lines.append(f"{cleaned_content}\n")
        return "".join(markdown_lines)


class DocumentLayoutSorter:
    def sort_blocks(self, blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        """Sắp xếp blocks theo Y trước, X sau — hỗ trợ thứ tự đọc đa cột."""
        return sorted(blocks, key=lambda b: (round(b.bbox.y1, 1), b.bbox.x1))


class LocalPDFParser:
    def __init__(self, sorter: DocumentLayoutSorter, thread_executor: ThreadPoolExecutor):
        self.sorter = sorter
        self.executor = thread_executor

    def _normalize_string(self, text: str) -> str:
        return re.sub(r"\s+", "", text).lower()

    def _detect_column_boundaries(self, page) -> List[Tuple[float, float]]:
        """Phát hiện ranh giới đa cột cục bộ."""
        if not page.chars:
            return [(0.0, float(page.width))]
        page_width = float(page.width)
        margin = page_width * 0.08
        bucket_size = 3.0
        buckets: Dict[int, int] = {}
        
        for char in page.chars:
            x = float(char.get("x0", 0))
            if margin <= x <= page_width - margin:
                b = int(x / bucket_size)
                buckets[b] = buckets.get(b, 0) + 1
                
        if not buckets:
            return [(0.0, page_width)]
            
        max_b = max(buckets.keys())
        gap_start = None
        gaps = []
        for b in range(int(margin / bucket_size), max_b + 1):
            if buckets.get(b, 0) == 0:
                if gap_start is None:
                    gap_start = b
            else:
                if gap_start is not None:
                    gap_end = b
                    gap_w = (gap_end - gap_start) * bucket_size
                    gap_cx = (gap_start + gap_end) / 2 * bucket_size
                    if gap_w > 15 and (page_width * 0.30) < gap_cx < (page_width * 0.70):
                        gaps.append((gap_cx, gap_w))
                    gap_start = None
                    
        if not gaps:
            return [(0.0, page_width)]
        best_gap_cx = max(gaps, key=lambda g: g[1])[0]
        return [(0.0, best_gap_cx), (best_gap_cx, page_width)]

    def _determine_block_type_by_font(
        self, text: str, font_size: float, font_name: str,
        most_used_size: float, max_size: float,
        most_used_font: str, bold_font_names: set,
    ) -> BlockType:
        cleaned = text.strip()
        if not cleaned:
            return BlockType.PARAGRAPH
        if cleaned.startswith(("- ", "* ", "• ", "● ")) or (
            len(cleaned) > 1 and re.match(r"^\d+[\.|\)]", cleaned)
        ):
            return BlockType.LIST_ITEM
        if font_size > most_used_size + 0.4:
            if font_size >= max_size - 0.5:
                return BlockType.HEADER_1
            return BlockType.HEADER_2
        if font_name and font_name != most_used_font:
            is_bold = (
                font_name in bold_font_names
                or "bold" in font_name.lower()
                or font_name.endswith("-Bold")
                or font_name.endswith("Bold")
            )
            if is_bold:
                if cleaned.startswith(("BƯỚC", "BUOC", "Step")):
                    return BlockType.HEADER_2
                if len(cleaned.split()) <= 10:
                    return BlockType.HEADER_1
                return BlockType.HEADER_2
        return BlockType.PARAGRAPH

    def _determine_block_type_ocr(
        self, line: TextLine, most_used_height: float, max_height: float
    ) -> BlockType:
        cleaned = line.text.strip()
        if not cleaned:
            return BlockType.PARAGRAPH
        if cleaned.startswith(("- ", "* ", "• ", "● ")) or (
            len(cleaned) > 1 and re.match(r"^\d+[\.|\)]", cleaned)
        ):
            return BlockType.LIST_ITEM
        h = line.font_size
        if h > most_used_height + 0.5:
            if h >= max_height - 0.5:
                return BlockType.HEADER_1
            return BlockType.HEADER_2
        if cleaned.startswith(("BƯỚC", "BUOC", "Step")):
            return BlockType.HEADER_2
        if cleaned.upper() == cleaned and re.search(r"[A-ZÀ-Ỷ]", cleaned) and len(cleaned.split()) <= 10:
            return BlockType.HEADER_1 if len(cleaned.split()) <= 5 else BlockType.HEADER_2
        return BlockType.PARAGRAPH

    def _execute_ocr_sync(self, page, resolution: int) -> List[dict]:
        """Tác vụ OCR chạy đồng bộ bên trong Worker Thread riêng biệt."""
        try:
            pil_img = page.to_image(resolution=resolution).original
        except Exception as e:
            logger.warning(f"Không thể render trang thành ảnh: {e}")
            return []

        scale = 72.0 / resolution
        try:
            from app.services.ocr.factory import OCRFactory
            engine = OCRFactory.get_engine()
            return engine.extract_words(pil_img, scale=scale)
        except Exception as e:
            logger.warning(f"OCR Engine xảy ra lỗi cục bộ: {e}")
            return []

    async def _extract_words_via_ocr_async(self, page, resolution: int = 150) -> List[dict]:
        """Bọc tiến trình OCR nặng nề vào mã bất đồng bộ để tránh chặn Event Loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._execute_ocr_sync, page, resolution)

    def _extract_line_font_info(self, cropped_page) -> Dict[str, dict]:
        result: Dict[str, dict] = {}
        try:
            words = cropped_page.extract_words(
                extra_attrs=["size", "fontname"],
                keep_blank_chars=False, x_tolerance=3, y_tolerance=3,
            )
            if not words:
                return result
            buckets: Dict[float, List[dict]] = defaultdict(list)
            for w in words:
                buckets[round(float(w.get("top", 0)), 1)].append(w)
            for _, lw in buckets.items():
                sw = sorted(lw, key=lambda x: x["x0"])
                line_text = " ".join(str(w["text"]) for w in sw).strip()
                if not line_text:
                    continue
                sizes = [float(w["size"]) for w in sw if w.get("size") and float(w["size"]) > 0]
                avg_size = sum(sizes) / len(sizes) if sizes else 0.0
                fc: Counter = Counter(w.get("fontname", "") for w in sw if w.get("fontname"))
                dominant = fc.most_common(1)[0][0] if fc else ""
                key = self._normalize_string(line_text)
                result[key] = {"size": avg_size, "fontname": dominant}
        except Exception as e:
            logger.debug(f"Thất bại khi trích xuất thông tin đặc trưng font: {e}")
        return result

    def _detect_columnar_table(self, line_map: dict, tolerance: float = 8.0) -> Optional[Tuple[int, int, List[List[str]]]]:
        sorted_tops = sorted(line_map.keys())
        if len(sorted_tops) < 3:
            return None

        def get_col_positions(ws):
            return sorted(set(round(w["x0"] / tolerance) * tolerance for w in ws))

        merged_map: dict = {}
        skip_tops = set()
        for i, top in enumerate(sorted_tops):
            if top in skip_tops:
                continue
            ws = line_map[top]
            if len(ws) <= 2 and i + 1 < len(sorted_tops):
                next_top = sorted_tops[i + 1]
                next_ws = line_map[next_top]
                if next_top - top < 12:
                    combined = sorted(ws + next_ws, key=lambda x: x["x0"])
                    merged_map[top] = combined
                    skip_tops.add(next_top)
                    continue
            merged_map[top] = ws

        merged_tops = sorted(merged_map.keys())
        final_map: dict = {}
        skip2 = set()
        for i, top in enumerate(merged_tops):
            if top in skip2:
                continue
            ws_cur = merged_map[top]
            if i + 1 < len(merged_tops):
                next_top = merged_tops[i + 1]
                if next_top - top < 20:
                    ws_next = merged_map[next_top]
                    if 2 <= len(ws_next) < len(ws_cur):
                        ws_cur_sorted = sorted(ws_cur, key=lambda x: x["x0"])
                        ws_next_sorted = sorted(ws_next, key=lambda x: x["x0"])
                        combined = [dict(w) for w in ws_cur_sorted]

                        boundaries = []
                        for ci in range(len(ws_cur_sorted) - 1):
                            x1_cur = ws_cur_sorted[ci].get("x1", ws_cur_sorted[ci]["x0"] + len(ws_cur_sorted[ci]["text"]) * 4.5)
                            x0_next = ws_cur_sorted[ci + 1]["x0"]
                            boundaries.append((x1_cur + x0_next) / 2)

                        def find_col_by_boundary(x):
                            for ci, bnd in enumerate(boundaries):
                                if x < bnd:
                                    return ci
                            return len(boundaries)

                        cell_col_map: dict = {}
                        for w_next in ws_next_sorted:
                            col_idx = find_col_by_boundary(w_next["x0"])
                            cell_col_map.setdefault(col_idx, []).append(w_next["text"])

                        for col_idx, texts in cell_col_map.items():
                            combined[col_idx] = dict(combined[col_idx])
                            combined[col_idx]["text"] = (combined[col_idx]["text"] + " " + " ".join(texts)).strip()

                        final_map[top] = combined
                        skip2.add(next_top)
                        continue
            final_map[top] = merged_map[top]

        merged_map = final_map
        sorted_merged = sorted(merged_map.keys())

        def cols_match(pos1, pos2, tol=tolerance * 2):
            if abs(len(pos1) - len(pos2)) > 1:
                return False
            common = min(len(pos1), len(pos2))
            return all(abs(pos1[i] - pos2[i]) <= tol for i in range(common))

        best_run: List = []
        best_run_start = None
        current_run: List = []
        current_run_start = None
        ref_cols = None

        for top in sorted_merged:
            ws = merged_map[top]
            cols = get_col_positions(ws)
            if len(cols) >= 3:
                if ref_cols is None:
                    ref_cols = cols
                    current_run_start = top
                    current_run = [ws]
                elif cols_match(cols, ref_cols):
                    current_run.append(ws)
                else:
                    if len(current_run) > len(best_run):
                        best_run = current_run
                        best_run_start = current_run_start
                    ref_cols = cols
                    current_run_start = top
                    current_run = [ws]
            else:
                if len(current_run) > len(best_run):
                    best_run = current_run
                    best_run_start = current_run_start
                ref_cols = None
                current_run_start = None
                current_run = []

        if len(current_run) > len(best_run):
            best_run = current_run
            best_run_start = current_run_start

        if len(best_run) < 3:
            return None

        all_x0 = []
        for ws in best_run:
            all_x0.extend(w["x0"] for w in ws)
        all_x0.sort()

        col_centers: List[float] = []
        for x in all_x0:
            if not col_centers or x - col_centers[-1] > tolerance:
                col_centers.append(x)
            else:
                col_centers[-1] = (col_centers[-1] + x) / 2

        def assign_col(x):
            return min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - x))

        rows: List[List[str]] = []
        for ws in best_run:
            row = [""] * len(col_centers)
            for w in ws:
                ci = assign_col(w["x0"])
                row[ci] = (row[ci] + " " + w["text"]).strip()
            rows.append(row)

        ncols_data = len(col_centers)
        header_rows: List[List[str]] = []
        original_run_start = best_run_start
        run_start_idx = sorted_merged.index(best_run_start)

        def is_header_candidate(ws):
            if len(ws) < 2 or len(ws) > ncols_data * 2:
                return False
            matches = 0
            for cx in col_centers:
                for w in ws:
                    if abs(w["x0"] - cx) <= tolerance:
                        matches += 1
                        break
            return matches >= max(3, int(ncols_data * 0.6))

        for i in range(run_start_idx - 1, -1, -1):
            top = sorted_merged[i]
            ws = merged_map[top]
            if best_run_start - top > 30:
                break
            if is_header_candidate(ws):
                row = [""] * len(col_centers)
                for w in ws:
                    ci = assign_col(w["x0"])
                    row[ci] = (row[ci] + " " + w["text"]).strip()
                header_rows.insert(0, row)
                best_run_start = top

        all_rows = header_rows + rows
        data_end_idx = sorted_merged.index(original_run_start) + len(best_run) - 1
        end_top = sorted_merged[min(data_end_idx, len(sorted_merged) - 1)]

        return (best_run_start, end_top, all_rows)

    def _process_text_band_mupdf(
        self, mupdf_blocks: List[dict], band_y1: float, band_y2: float,
        page_width: float, most_used_font_size: float, max_font_size: float,
    ) -> List[DocumentBlock]:
        """
        Xử lý band text dùng pymupdf blocks — chất lượng unicode tốt hơn.
        mupdf_blocks: list blocks từ MuPDFTextExtractor.get_page_blocks() đã lọc theo band.
        """
        blocks: List[DocumentBlock] = []
        if not mupdf_blocks:
            return blocks

        # Lọc blocks trong band này
        band_blocks = [
            b for b in mupdf_blocks
            if band_y1 <= (b["y0"] + b["y1"]) / 2 <= band_y2
        ]
        if not band_blocks:
            return blocks

        # Phân loại từng line dựa trên font_size và bold flag
        for b in band_blocks:
            text = PDFTextCleaner.clean(b["text"].strip())
            if not text:
                continue

            font_size = b["font_size"]
            is_bold = b["bold"]

            # Phân loại block type
            if text.startswith(("- ", "* ", "• ", "● ", "– ")) or (
                len(text) > 1 and re.match(r"^\d+[\.|\)]", text)
            ):
                btype = BlockType.LIST_ITEM
            elif text.startswith("•"):
                # Bullet point từ pymupdf
                text = "- " + text[1:].strip()
                btype = BlockType.LIST_ITEM
            elif font_size > most_used_font_size + 0.4:
                if font_size >= max_font_size - 0.5:
                    btype = BlockType.HEADER_1
                else:
                    btype = BlockType.HEADER_2
            elif is_bold:
                if text.startswith(("BƯỚC", "BUOC", "Step")):
                    btype = BlockType.HEADER_2
                elif len(text.split()) <= 10:
                    btype = BlockType.HEADER_1
                else:
                    btype = BlockType.HEADER_2
            else:
                btype = BlockType.PARAGRAPH

            blocks.append(DocumentBlock(
                block_type=btype,
                bbox=BoundingBox(b["x0"], b["y0"], b["x1"], b["y1"]),
                content=text,
            ))
        return blocks

    def _process_text_band(
        self, cropped_page, band_y1: float, band_y2: float,
        page_width: float, most_used_font_size: float, most_used_font_name: str,
        max_font_size: float, bold_font_names: set,
    ) -> List[DocumentBlock]:
        blocks: List[DocumentBlock] = []
        text_content = cropped_page.extract_text(x_tolerance=3, y_tolerance=3)
        use_layout = False
        
        if text_content:
            words_normal = text_content.split()
            long_no_space = sum(1 for w in words_normal if len(w) > 15)
            if len(words_normal) > 0 and long_no_space / len(words_normal) > 0.08:
                use_layout = True
                fine_words = cropped_page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
                if fine_words:
                    line_map: dict = defaultdict(list)
                    for w in fine_words:
                        top_key = round(float(w.get("top", 0)), 0)
                        line_map[top_key].append(w)

                    table_result = self._detect_columnar_table(line_map)
                    table_top_range = set()
                    if table_result:
                        t_start, t_end, t_rows = table_result
                        md_table = TableConverter.to_markdown(t_rows)
                        if md_table:
                            blocks.append(DocumentBlock(
                                block_type=BlockType.TABLE,
                                bbox=BoundingBox(0.0, t_start, page_width, t_end),
                                content=md_table,
                            ))
                        for top in line_map.keys():
                            if t_start - 1 <= top <= t_end + 15:
                                table_top_range.add(top)

                    rebuilt_lines = []
                    line_y_positions = []
                    for top_key in sorted(line_map.keys()):
                        if top_key in table_top_range:
                            continue
                        line_words = sorted(line_map[top_key], key=lambda w: w["x0"])
                        line_text = " ".join(w["text"] for w in line_words)
                        rebuilt_lines.append(line_text)
                        line_y_positions.append(top_key)
                    text_content = "\n".join(rebuilt_lines) if rebuilt_lines else ""

        if not text_content:
            return blocks

        font_info = self._extract_line_font_info(cropped_page)

        def lookup_font(text: str) -> dict:
            key = self._normalize_string(text)
            if key in font_info:
                return font_info[key]
            for k, v in font_info.items():
                if k in key or key in k:
                    return v
            return {}

        _line_y_pos = line_y_positions if use_layout else []
        raw_lines = text_content.split("\n")
        merged: List[dict] = []
        acc: List[str] = []
        acc_is_header = False
        acc_y: float = band_y1

        def flush():
            nonlocal acc_is_header, acc_y
            if acc:
                merged.append({"text": " ".join(acc), "is_header": acc_is_header, "y": acc_y})
                acc.clear()

        for line_idx, line in enumerate(raw_lines):
            cleaned = line.strip()
            if not cleaned:
                continue
            current_y = _line_y_pos[line_idx] if line_idx < len(_line_y_pos) else band_y1

            is_list = cleaned.startswith(("- ", "* ", "• ", "● ")) or bool(re.match(r"^\d+[\.|\)]", cleaned))
            fi = lookup_font(cleaned)
            lsize = fi.get("size", most_used_font_size)
            lfont = fi.get("fontname", most_used_font_name)
            is_bold = (lfont != most_used_font_name and ("bold" in lfont.lower() or lfont in bold_font_names)) or lsize > most_used_font_size + 0.4

            if use_layout:
                merged.append({"text": cleaned, "is_header": is_bold, "y": current_y})
                continue

            if is_list:
                flush()
                acc_is_header = False
                merged.append({"text": cleaned, "is_header": False, "y": current_y})
            elif is_bold:
                if acc_is_header:
                    acc.append(cleaned)
                else:
                    flush()
                    acc.append(cleaned)
                    acc_is_header = True
                    acc_y = current_y
            else:
                if acc_is_header:
                    flush()
                    acc_is_header = False
                    acc.append(cleaned)
                    acc_y = current_y
                else:
                    if acc:
                        last_line = acc[-1]
                        ends_punc = last_line[-1] in ".!?:" if last_line else False
                        starts_lower = cleaned[0].islower() if cleaned else False
                        if not ends_punc or starts_lower:
                            acc.append(cleaned)
                        else:
                            flush()
                            acc.append(cleaned)
                            acc_y = current_y
                    else:
                        acc.append(cleaned)
                        acc_y = current_y
        flush()

        for entry in merged:
            lt = entry["text"]
            fi = lookup_font(lt)
            lsize = fi.get("size", most_used_font_size)
            lfont = fi.get("fontname", most_used_font_name)
            btype = self._determine_block_type_by_font(
                lt, lsize, lfont, most_used_font_size, max_font_size,
                most_used_font_name, bold_font_names,
            )
            entry_y = entry.get("y", band_y1)
            blocks.append(DocumentBlock(
                block_type=btype,
                bbox=BoundingBox(0.0, entry_y, page_width, entry_y + 10),
                content=lt,
            ))
        return blocks

    async def _process_page_column_async(
        self, page, page_idx: int,
        col_x1: float, col_x2: float,
        most_used_font_size: float, most_used_font_name: str,
        max_font_size: float, bold_font_names: set,
        image_output_dir: Optional[str],
        block_counter_ref: List[int],
        mupdf_blocks: Optional[List[dict]] = None,
    ) -> List[DocumentBlock]:
        col_blocks: List[DocumentBlock] = []
        page_area = float(page.width) * float(page.height)

        raw_elements = []
        tables = page.find_tables()
        for table in tables:
            tx1, ty1, tx2, ty2 = table.bbox
            if col_x1 <= (tx1 + tx2) / 2 <= col_x2:
                raw_elements.append({"y1": float(ty1), "y2": float(ty2), "type": "table", "data": table})

        for img in page.images:
            y1, y2 = float(img["top"]), float(img["bottom"])
            x0, x1 = float(img["x0"]), float(img["x1"])
            w, h = x1 - x0, y2 - y1
            if h <= 0 or w <= 0 or w < 10 or h < 10:
                continue
            if (w * h) / page_area > 0.90:
                continue
            if col_x1 <= (x0 + x1) / 2 <= col_x2:
                raw_elements.append({"y1": y1, "y2": y2, "type": "image", "data": img})

        raw_elements.sort(key=lambda e: e["y1"])
        merged_intervals = []
        for el in raw_elements:
            if not merged_intervals or el["y1"] > merged_intervals[-1]["y2"] + 3.0:
                merged_intervals.append({"y1": el["y1"], "y2": el["y2"], "elements": [el]})
            else:
                last = merged_intervals[-1]
                last["y2"] = max(last["y2"], el["y2"])
                last["elements"].append(el)

        bands = []
        cur_y = 0.0
        page_h = float(page.height)
        for iv in merged_intervals:
            if iv["y1"] > cur_y + 1.0:
                bands.append({"type": "text", "y1": cur_y, "y2": iv["y1"]})
            bands.append({"type": "exclusion", "y1": iv["y1"], "y2": iv["y2"], "elements": iv["elements"]})
            cur_y = iv["y2"]
        if cur_y < page_h - 1.0:
            bands.append({"type": "text", "y1": cur_y, "y2": page_h})

        words = page.extract_words(keep_blank_chars=False)
        is_scanned = False
        if not words:
            # Chạy tác vụ OCR bất đồng bộ không gây nghẽn hệ thống
            words = await self._extract_words_via_ocr_async(page)
            is_scanned = bool(words)

        ocr_most_used_h, ocr_max_h = 10.0, 10.0
        if is_scanned and words:
            all_lines_for_stats = TextLineGrouper.group(words)
            if all_lines_for_stats:
                heights = [round(line.font_size * 2) / 2 for line in all_lines_for_stats if line.font_size > 0]
                if heights:
                    ocr_most_used_h = Counter(heights).most_common(1)[0][0]
                    ocr_max_h = max(heights)

        for band in bands:
            if band["type"] == "text":
                crop = page.crop((col_x1, band["y1"], col_x2, band["y2"]), relative=False)
                if is_scanned:
                    bw = [w for w in words
                          if col_x1 <= (w["x0"] + w["x1"]) / 2 <= col_x2
                          and band["y1"] <= (w["top"] + w["bottom"]) / 2 <= band["y2"]]
                    for line in TextLineGrouper.group(bw):
                        col_blocks.append(DocumentBlock(
                            block_type=self._determine_block_type_ocr(line, ocr_most_used_h, ocr_max_h),
                            bbox=line.bbox, content=line.text,
                        ))
                elif mupdf_blocks is not None:
                    # Dùng pymupdf blocks — unicode tốt hơn, không bị encode artifact
                    mupdf_band = [
                        b for b in mupdf_blocks
                        if col_x1 <= (b["x0"] + b["x1"]) / 2 <= col_x2
                        and band["y1"] <= (b["y0"] + b["y1"]) / 2 <= band["y2"]
                    ]
                    col_blocks.extend(self._process_text_band_mupdf(
                        mupdf_band, band["y1"], band["y2"],
                        col_x2 - col_x1, most_used_font_size, max_font_size,
                    ))
                else:
                    col_blocks.extend(self._process_text_band(
                        crop, band["y1"], band["y2"], col_x2 - col_x1,
                        most_used_font_size, most_used_font_name,
                        max_font_size, bold_font_names,
                    ))
            elif band["type"] == "exclusion":
                for el in sorted(
                    band["elements"],
                    key=lambda e: (
                        e["data"].bbox[0] if e["type"] == "table" and e["data"].bbox is not None
                        else e["data"]["x0"]
                    )
                ):
                    if el["type"] == "table":
                        raw = el["data"].extract()
                        if raw:
                            col_blocks.append(DocumentBlock(
                                block_type=BlockType.TABLE,
                                bbox=BoundingBox(*el["data"].bbox),
                                content=TableConverter.to_markdown(raw),
                            ))
                    elif el["type"] == "image":
                        img = el["data"]
                        bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                        safe_bbox = (
                            max(0.0, bbox[0]),
                            max(0.0, bbox[1]),
                            min(float(page.width), bbox[2]),
                            min(float(page.height), bbox[3]),
                        )

                        # Luôn OCR ảnh để lấy nội dung text
                        ocr_text = ""
                        try:
                            pil_img = page.crop(safe_bbox).to_image(resolution=150).original
                            from app.services.ocr.ocr_utils import ocr_image_to_text
                            ocr_text = ocr_image_to_text(pil_img)
                        except Exception as e:
                            logger.debug(f"Không thể OCR ảnh: {e}")

                        # Lưu file ảnh chỉ khi có image_output_dir
                        saved_path = ""
                        if image_output_dir:
                            os.makedirs(image_output_dir, exist_ok=True)
                            block_counter_ref[0] += 1
                            name = f"page_{page_idx + 1}_img_{block_counter_ref[0]}.png"
                            saved_path = os.path.join(image_output_dir, name)
                            try:
                                page.crop(safe_bbox).to_image(resolution=150).save(saved_path)
                            except Exception as e:
                                logger.warning(f"Không thể lưu ảnh {saved_path}: {e}")
                                saved_path = ""

                        col_blocks.append(DocumentBlock(
                            block_type=BlockType.IMAGE,
                            bbox=BoundingBox(*bbox),
                            content=saved_path,   # "" nếu không lưu
                            ocr_text=ocr_text,    # "" nếu OCR không ra gì
                        ))
        return col_blocks

    async def parse_async(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        image_output_dir: Optional[str] = None,
    ) -> List[DocumentBlock]:
        """
        Args:
            pdf_path: Đường dẫn file PDF đầu vào.
            output_dir: Thư mục chứa file .md và các file phụ. Không dùng để quyết định lưu ảnh.
            image_output_dir: Nếu None → không lưu ảnh, chỉ OCR text từ ảnh.
                              Nếu có path → lưu ảnh vào thư mục này VÀ OCR.
        """
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError("Vui lòng cài đặt thư viện phân tích cấu trúc: pip install pdfplumber") from exc

        extracted_blocks: List[DocumentBlock] = []
        # image_output_dir = None → không lưu ảnh, chỉ OCR nội dung
        # image_output_dir = "path/images" → lưu ảnh VÀ OCR
        img_counter = [0]

        # Mở pymupdf song song với pdfplumber để lấy text chất lượng cao
        use_mupdf = MuPDFTextExtractor.available()
        fitz_doc = None
        mupdf_font_stats = None
        if use_mupdf:
            try:
                import fitz
                fitz_doc = fitz.open(pdf_path)
                mupdf_font_stats = MuPDFTextExtractor.compute_font_stats_from_doc(fitz_doc)
                logger.info(
                    f"pymupdf available — font stats: "
                    f"most_used={mupdf_font_stats['most_used']:.1f}pt, "
                    f"max={mupdf_font_stats['max']:.1f}pt"
                )
            except Exception as e:
                logger.warning(f"pymupdf init failed, falling back to pdfplumber: {e}")
                use_mupdf = False
                fitz_doc = None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                font_stats = FontStatsAnalyzer.analyze(pdf)
                mfs = font_stats["most_used_font_size"]
                mfn = font_stats["most_used_font_name"]
                maxfs = font_stats["max_font_size"]
                bold_fonts = font_stats["bold_font_names"]

                # Nếu có pymupdf, dùng font stats của nó (chính xác hơn)
                if mupdf_font_stats:
                    mfs = mupdf_font_stats["most_used"]
                    maxfs = mupdf_font_stats["max"]

                logger.info(f"Body font: {mfn} | size: {mfs}pt | max: {maxfs}pt | bold: {bold_fonts}")

                for page_idx, page in enumerate(pdf.pages):
                    logger.info(f"Đang phân tích cấu trúc trang {page_idx + 1}/{len(pdf.pages)}")

                    # Lấy pymupdf blocks cho trang này (nếu có)
                    mupdf_page_blocks = None
                    if use_mupdf and fitz_doc and page_idx < len(fitz_doc):
                        try:
                            mupdf_page_blocks = MuPDFTextExtractor.get_page_blocks(fitz_doc[page_idx])
                        except Exception as e:
                            logger.debug(f"pymupdf page {page_idx+1} error: {e}")

                    columns = self._detect_column_boundaries(page)
                    for col_x1, col_x2 in columns:
                        col_blocks = await self._process_page_column_async(
                            page, page_idx, col_x1, col_x2,
                            mfs, mfn, maxfs, bold_fonts,
                            image_output_dir, img_counter,
                            mupdf_blocks=mupdf_page_blocks,
                        )
                        extracted_blocks.extend(col_blocks)
        finally:
            if fitz_doc:
                fitz_doc.close()

        return self.sorter.sort_blocks(extracted_blocks)

class LocalCoreEngine:
    def __init__(self):
        self.sorter = DocumentLayoutSorter()
        # Khởi tạo ThreadPool gồm 4 Core Workers xử lý OCR nền
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.pdf_parser = LocalPDFParser(self.sorter, self.executor)

    async def extract_markdown_string_async(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        image_output_dir: Optional[str] = None,
    ) -> str:
        """
        Args:
            image_output_dir: None (mặc định) → không lưu ảnh, chỉ OCR.
                              Truyền path → lưu ảnh vào thư mục đó.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Không tìm thấy file nguồn yêu cầu: {pdf_path}")
        parsed_blocks = await self.pdf_parser.parse_async(
            pdf_path,
            output_dir=output_dir,
            image_output_dir=image_output_dir,
        )
        return MarkdownCompiler.compile(parsed_blocks)

    async def convert_pdf_to_markdown_async(
        self,
        pdf_path: str,
        output_md_path: str,
        image_output_dir: Optional[str] = None,
    ) -> None:
        """
        Args:
            image_output_dir: None → không lưu ảnh. Có path → lưu ảnh vào path đó.
        """
        logger.info(f"Khởi động tiến trình chuyển đổi: {pdf_path}")
        output_dir = os.path.dirname(output_md_path) or "."
        os.makedirs(output_dir, exist_ok=True)
        md = await self.extract_markdown_string_async(
            pdf_path,
            output_dir=output_dir,
            image_output_dir=image_output_dir,
        )
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info(f"Hoàn tất lưu trữ cấu trúc: {output_md_path}")
        
    def shutdown(self):
        """Giải phóng tài nguyên ThreadPool khi tắt ứng dụng API."""
        self.executor.shutdown(wait=True)

@register(".pdf")
def pdf_to_markdown(file_path: str | Path, output_dir: str) -> str:
    """
    Được gọi bởi DocumentParserPipeline.
    Không lưu ảnh theo mặc định — chỉ OCR ảnh để lấy text.
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = Path(file_path).stem
    output_md_path = os.path.join(output_dir, f"{base_name}.md")
    engine = LocalCoreEngine()
    try:
        md = asyncio.run(engine.extract_markdown_string_async(
            str(file_path),
            output_dir=output_dir,
            image_output_dir=None,  # mặc định không lưu ảnh
        ))
    finally:
        engine.shutdown()
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md


if __name__ == "__main__":
    import sys
    # Cách dùng:
    #   python -m app.services.document_parser.pdf_converter input.pdf output.md
    #       → không lưu ảnh, chỉ OCR ảnh → ghi <img> """text"""
    #
    #   python -m app.services.document_parser.pdf_converter input.pdf output.md ./images
    #       → lưu ảnh vào ./images/, OCR rồi ghi <img> """text""" hoặc <img> đường_dẫn
    target = sys.argv[1] if len(sys.argv) > 1 else "document.pdf"
    out    = sys.argv[2] if len(sys.argv) > 2 else "output.md"
    img_dir = sys.argv[3] if len(sys.argv) > 3 else None  # optional

    if os.path.exists(target):
        core_engine = LocalCoreEngine()
        asyncio.run(core_engine.convert_pdf_to_markdown_async(
            target, out, image_output_dir=img_dir
        ))
        core_engine.shutdown()
    else:
        logger.warning(f"Không tìm thấy tệp tin đầu vào: {target}")
        logger.warning(f"Không tìm thấy tệp tin đầu vào: {target}")