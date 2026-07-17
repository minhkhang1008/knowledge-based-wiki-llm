import os
import re
import logging
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, TypeVar
from app.services.document_parser.converter_registry import register

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pdf_converter")

T = TypeVar("T")


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


@dataclass
class TextLine:
    text: str
    bbox: BoundingBox
    font_size: float
    words: List[dict]


class DocumentLayoutSorter:
    """
    Giữ lại lớp cấu trúc Sorter để đảm bảo tính tương thích ngược với hệ thống Core,
    tuy nhiên quá trình phân bổ thứ tự đọc đã được xử lý triệt để ngay từ bước phân đoạn dải ngang.
    """
    def sort_blocks(self, blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        return blocks


class MarkdownCompiler:
    @staticmethod
    def compile(blocks: List[DocumentBlock]) -> str:
        markdown_lines: List[str] = []
        
        for block in blocks:
            cleaned_content = block.content.strip()
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
            elif block.block_type == BlockType.IMAGE:
                image_filename = os.path.basename(block.content)
                markdown_lines.append(f"\n![Hình ảnh trực quan](images/{image_filename})\n")
            else:
                markdown_lines.append(f"{cleaned_content}\n")
                
        return "".join(markdown_lines)


class LocalPDFParser:
    def __init__(self, sorter: DocumentLayoutSorter):
        self.sorter = sorter

    def _compute_font_stats(self, pdf) -> dict:
        """
        Phân tích thống kê font của toàn tài liệu để xác định:
        - most_used_font_size: font size phổ biến nhất (body text)
        - most_used_font_name: font name phổ biến nhất (body text)
        - max_font_size: font size lớn nhất (có thể là tiêu đề)
        - bold_font_names: tập hợp các font name có chứa 'Bold' hoặc 'bold'
        Giống cách DetectHeaders.jsx trong pdf-to-markdown dùng mostUsedHeight và mostUsedFont.
        """
        from collections import Counter
        size_counter: Counter = Counter()
        font_counter: Counter = Counter()
        bold_font_names = set()
        max_font_size = 0.0

        for page in pdf.pages:
            for char in page.chars:
                size = char.get("size")
                fname = char.get("fontname", "")
                if size and float(size) > 0:
                    rounded = round(float(size) * 2) / 2
                    size_counter[rounded] += 1
                    font_counter[fname] += 1
                    if float(size) > max_font_size:
                        max_font_size = float(size)
                    # Nhận diện font bold dựa trên tên
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

    def _determine_block_type_by_font(
        self,
        text: str,
        font_size: float,
        font_name: str,
        most_used_size: float,
        max_size: float,
        most_used_font: str,
        bold_font_names: set,
    ) -> BlockType:
        """
        Phân loại block dựa trên font size VÀ font name (digital PDF).
        Logic tham khảo từ DetectHeaders.jsx của pdf-to-markdown:
        - font_size > most_used_size  → header theo kích thước
        - font_name khác most_used_font VÀ là bold → header theo trọng lượng
        List item luôn được kiểm tra trước.
        """
        cleaned = text.strip()
        if not cleaned:
            return BlockType.PARAGRAPH

        # List item luôn được kiểm tra trước, bất kể font
        if cleaned.startswith(("- ", "* ", "• ", "● ")) or (
            len(cleaned) > 1 and re.match(r"^\d+[\.|\)]", cleaned)
        ):
            return BlockType.LIST_ITEM

        # Phân loại header dựa trên font size tương đối
        if font_size > most_used_size + 0.4:
            threshold_h2 = most_used_size + (max_size - most_used_size) / 4
            if font_size >= max_size - 0.5:
                return BlockType.HEADER_1
            elif font_size >= threshold_h2:
                return BlockType.HEADER_2
            else:
                return BlockType.HEADER_2

        # Phân loại header dựa trên font name (bold font ≠ body font)
        # Đây là trường hợp khi PDF dùng font size đồng nhất nhưng phân biệt bằng Bold/Regular
        if font_name and font_name != most_used_font:
            is_bold = (
                font_name in bold_font_names
                or "bold" in font_name.lower()
                or font_name.endswith("-Bold")
                or font_name.endswith("Bold")
            )
            if is_bold:
                # BƯỚC x, Step x → H2 vì là section heading
                if cleaned.startswith("BƯỚC") or cleaned.startswith("BUOC") or cleaned.startswith("Step"):
                    return BlockType.HEADER_2
                # Tiêu đề ngắn (≤ 10 từ) → H1, dài hơn → H2
                if len(cleaned.split()) <= 10:
                    return BlockType.HEADER_1
                return BlockType.HEADER_2

        return BlockType.PARAGRAPH

    def _determine_block_type_simple(self, text: str) -> BlockType:
        """
        Fallback: Phân loại khối văn bản chỉ dựa trên heuristic chuỗi ký tự.
        Chỉ dùng cho OCR (scanned PDF) khi không có thông tin font size.
        """
        cleaned = text.strip()
        if not cleaned:
            return BlockType.PARAGRAPH

        if cleaned.startswith(("- ", "* ", "• ", "● ")) or (
            len(cleaned) > 1 and re.match(r"^\d+[\.|\)]", cleaned)
        ):
            return BlockType.LIST_ITEM

        if cleaned.startswith("BƯỚC") or cleaned.startswith("BUOC") or cleaned.startswith("Step"):
            return BlockType.HEADER_2

        if cleaned.upper() == cleaned and re.search(r"[A-ZÀ-Ỷ]", cleaned) and len(cleaned.split()) <= 10:
            if len(cleaned.split()) <= 5:
                return BlockType.HEADER_1
            return BlockType.HEADER_2

        return BlockType.PARAGRAPH

    def _convert_table_to_markdown(self, raw_table: List[List[Optional[str]]]) -> str:
        if not raw_table or not raw_table[0]:
            return ""

        headers = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in raw_table[0]]
        separator = ["---"] * len(headers)
        
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |"
        ]

        for row in raw_table[1:]:
            row_cells = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
            lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines)

    def _extract_words_via_ocr(self, page, resolution: int = 150) -> List[dict]:
        """
        Pipeline dự phòng OCR khi tài liệu PDF mục tiêu là tài liệu quét không có Text Layer.
        """
        try:
            import pytesseract
        except ImportError:
            logger.error("Hệ thống thiếu thư viện 'pytesseract'. Vui lòng thực thi lệnh: pip install pytesseract")
            return []

        try:
            image_obj = page.to_image(resolution=resolution)
            pil_img = image_obj.original
            
            ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            extracted_words: List[dict] = []
            scale_factor = 72.0 / resolution
            
            for i in range(len(ocr_data["text"])):
                text_content = str(ocr_data["text"][i]).strip()
                confidence = float(ocr_data["conf"][i])
                
                if not text_content or confidence < 40.0:
                    continue
                
                x0 = float(ocr_data["left"][i]) * scale_factor
                top = float(ocr_data["top"][i]) * scale_factor
                x1 = (float(ocr_data["left"][i]) + float(ocr_data["width"][i])) * scale_factor
                bottom = (float(ocr_data["top"][i]) + float(ocr_data["height"][i])) * scale_factor
                
                extracted_words.append({
                    "text": text_content,
                    "x0": x0,
                    "top": top,
                    "x1": x1,
                    "bottom": bottom
                })
            return extracted_words
        except Exception as e:
            logger.error(f"Lỗi hệ thống trong quá trình thực thi OCR Fallback Pipeline: {e}")
            return []

    def _group_words_to_lines(self, words: List[dict]) -> List[TextLine]:
        """
        Hàm gom dòng từ danh sách từ khóa, chỉ kích hoạt khi xử lý OCR Fallback của tài liệu quét.
        """
        sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
        lines: List[List[dict]] = []
        bounds: List[Tuple[float, float]] = []

        for word in sorted_words:
            top = float(word["top"])
            bottom = float(word["bottom"])
            height = bottom - top
            if height <= 0:
                continue

            matched_index = None
            for idx, (line_top, line_bottom) in enumerate(bounds):
                overlap_top = max(top, line_top)
                overlap_bottom = min(bottom, line_bottom)
                overlap_height = max(0.0, overlap_bottom - overlap_top)
                min_height = min(height, line_bottom - line_top)
                if min_height > 0 and (overlap_height / min_height) > 0.5:
                    matched_index = idx
                    break

            if matched_index is None:
                lines.append([word])
                bounds.append((top, bottom))
            else:
                lines[matched_index].append(word)
                line_top, line_bottom = bounds[matched_index]
                bounds[matched_index] = (min(line_top, top), max(line_bottom, bottom))

        text_lines: List[TextLine] = []
        for line_words in lines:
            sorted_line_words = sorted(line_words, key=lambda w: w["x0"])
            text = " ".join(str(w["text"]) for w in sorted_line_words)
            if not text:
                continue

            x1 = min(w["x0"] for w in sorted_line_words)
            y1 = min(w["top"] for w in sorted_line_words)
            x2 = max(w["x1"] for w in sorted_line_words)
            y2 = max(w["bottom"] for w in sorted_line_words)
            avg_font_size = sum(float(w["bottom"]) - float(w["top"]) for w in sorted_line_words) / len(sorted_line_words)

            text_lines.append(TextLine(
                text=text,
                bbox=BoundingBox(x1, y1, x2, y2),
                font_size=avg_font_size,
                words=sorted_line_words
            ))

        return text_lines

    def _extract_line_font_info(self, cropped_page) -> Dict[str, dict]:
        """
        Trích xuất font size và font name trung bình/phổ biến cho từng dòng văn bản.
        Key là text của dòng (strip), value là dict {"size": float, "fontname": str}.
        Dùng extra_attrs để pdfplumber trả về thuộc tính 'size' và 'fontname' từng word.
        """
        line_info: Dict[str, dict] = {}
        try:
            words_with_attrs = cropped_page.extract_words(
                extra_attrs=["size", "fontname"],
                keep_blank_chars=False,
                x_tolerance=3,
                y_tolerance=3
            )
            if not words_with_attrs:
                return line_info

            from collections import defaultdict, Counter
            line_buckets: Dict[float, List[dict]] = defaultdict(list)
            for w in words_with_attrs:
                top_key = round(float(w.get("top", 0)), 1)
                line_buckets[top_key].append(w)

            for top_key, line_words in line_buckets.items():
                sorted_words = sorted(line_words, key=lambda x: x["x0"])
                line_text = " ".join(str(w["text"]) for w in sorted_words).strip()
                if not line_text:
                    continue
                sizes = [float(w["size"]) for w in sorted_words if w.get("size") and float(w["size"]) > 0]
                avg_size = sum(sizes) / len(sizes) if sizes else 0.0
                # Font name phổ biến nhất của dòng
                font_counter: Counter = Counter(
                    w.get("fontname", "") for w in sorted_words if w.get("fontname")
                )
                dominant_font = font_counter.most_common(1)[0][0] if font_counter else ""
                line_info[line_text] = {"size": avg_size, "fontname": dominant_font}
        except Exception as e:
            logger.debug(f"Không thể trích xuất font info cho vùng crop: {e}")
        return line_info

    def parse(self, pdf_path: str, output_dir: Optional[str] = None) -> List[DocumentBlock]:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError("Thư viện 'pdfplumber' chưa được cài đặt. Vui lòng chạy: pip install pdfplumber") from exc

        extracted_blocks: List[DocumentBlock] = []
        image_output_dir = os.path.join(output_dir, "images") if output_dir else None

        with pdfplumber.open(pdf_path) as pdf:
            # Pass 1: Tính thống kê font toàn tài liệu (font size + font name + bold)
            font_stats = self._compute_font_stats(pdf)
            most_used_font_size = font_stats["most_used_font_size"]
            most_used_font_name = font_stats["most_used_font_name"]
            max_font_size = font_stats["max_font_size"]
            bold_font_names = font_stats["bold_font_names"]
            logger.info(
                f"Font size phổ biến: {most_used_font_size}pt | Lớn nhất: {max_font_size}pt | "
                f"Body font: {most_used_font_name} | Bold fonts: {bold_font_names}"
            )

            for page_idx, page in enumerate(pdf.pages):
                logger.info(f"Đang phân tích Trang {page_idx + 1}/{len(pdf.pages)}")
                
                page_area = float(page.width) * float(page.height)
                raw_elements = []

                # Bước 1: Thu thập tọa độ và dữ liệu của tất cả các bảng biểu trên trang
                tables = page.find_tables()
                for table in tables:
                    raw_elements.append({
                        "y1": float(table.bbox[1]),
                        "y2": float(table.bbox[3]),
                        "type": "table",
                        "data": table
                    })

                # Bước 2: Thu thập tọa độ của tất cả các ảnh (loại trừ ảnh nền trang trí lớn > 90% diện tích trang)
                for img in page.images:
                    y1 = float(img["top"])
                    y2 = float(img["bottom"])
                    x0 = float(img["x0"])
                    x1 = float(img["x1"])
                    w = x1 - x0
                    h = y2 - y1
                    if h <= 0 or w <= 0:
                        continue
                    if (w * h) / page_area > 0.90:
                        continue
                    raw_elements.append({
                        "y1": y1,
                        "y2": y2,
                        "type": "image",
                        "data": img
                    })

                # Bước 3: Sắp xếp và hợp nhất các khoảng tọa độ Y bị chồng lấn (Overlap)
                raw_elements.sort(key=lambda e: e["y1"])
                merged_intervals = []
                for el in raw_elements:
                    if not merged_intervals:
                        merged_intervals.append({
                            "y1": el["y1"],
                            "y2": el["y2"],
                            "elements": [el]
                        })
                    else:
                        last = merged_intervals[-1]
                        # Hợp nhất nếu dải chặn Y bị đè lên nhau hoặc quá gần nhau (ngưỡng dung sai 3 point)
                        if el["y1"] <= last["y2"] + 3.0:
                            last["y2"] = max(last["y2"], el["y2"])
                            last["elements"].append(el)
                        else:
                            merged_intervals.append({
                                "y1": el["y1"],
                                "y2": el["y2"],
                                "elements": [el]
                            })

                # Bước 4: Tạo cấu trúc các dải ngang (Bands) xen kẽ nhau tuần tự từ trên xuống dưới
                bands = []
                current_y = 0.0
                page_height = float(page.height)

                for interval in merged_intervals:
                    if interval["y1"] > current_y + 1.0:
                        bands.append({
                            "type": "text",
                            "y1": current_y,
                            "y2": interval["y1"]
                        })
                    bands.append({
                        "type": "exclusion",
                        "y1": interval["y1"],
                        "y2": interval["y2"],
                        "elements": interval["elements"]
                    })
                    current_y = interval["y2"]

                if current_y < page_height - 1.0:
                    bands.append({
                        "type": "text",
                        "y1": current_y,
                        "y2": page_height
                    })

                # Bước 5: Kiểm tra xem PDF gốc có Text Layer hay không
                words = page.extract_words(keep_blank_chars=False)
                is_scanned = False
                if not words:
                    logger.info(f"Kích hoạt OCR engine cho trang quét {page_idx + 1}")
                    words = self._extract_words_via_ocr(page, resolution=150)
                    if words:
                        is_scanned = True

                # Bước 6: Phân tích và trích xuất dữ liệu chi tiết theo từng dải
                for band in bands:
                    if band["type"] == "text":
                        if is_scanned:
                            # Phân luồng xử lý tài liệu quét (Scanned PDF) bằng OCR
                            band_words = [
                                w for w in words 
                                if band["y1"] <= (w["top"] + w["bottom"]) / 2 <= band["y2"]
                            ]
                            if band_words:
                                lines = self._group_words_to_lines(band_words)
                                for line in lines:
                                    block_type = self._determine_block_type_simple(line.text)
                                    extracted_blocks.append(
                                        DocumentBlock(
                                            block_type=block_type,
                                            bbox=line.bbox,
                                            content=line.text
                                        )
                                    )
                        else:
                            # Phân luồng xử lý tài liệu số (Digital PDF): Trích xuất cục bộ tuyệt đối chính xác bằng Native Engine
                            cropped_page = page.crop((0, band["y1"], page.width, band["y2"]), relative=False)
                            text_content = cropped_page.extract_text(x_tolerance=3, y_tolerance=3)

                            # Trích xuất font info (size + fontname) cho từng dòng trong vùng band này
                            line_font_info = self._extract_line_font_info(cropped_page)
                            
                            if text_content:
                                raw_lines = text_content.split("\n")
                                # Mỗi entry: {"text": str, "is_header": bool, "is_list": bool}
                                merged_lines: List[dict] = []
                                current_accumulator: List[str] = []
                                current_acc_is_header: bool = False

                                def flush_accumulator():
                                    if current_accumulator:
                                        merged_lines.append({
                                            "text": " ".join(current_accumulator),
                                            "is_header": current_acc_is_header,
                                        })
                                        current_accumulator.clear()

                                # Giải thuật gộp các dòng bị ngắt dòng vật lý của cùng một đoạn văn
                                for line in raw_lines:
                                    cleaned = line.strip()
                                    if not cleaned:
                                        continue

                                    is_list = (
                                        cleaned.startswith(("- ", "* ", "• ", "● ")) or
                                        bool(re.match(r"^\d+[\.|\)]", cleaned))
                                    )

                                    # Lấy font info của dòng vật lý này
                                    line_info = line_font_info.get(cleaned, {})
                                    line_size = line_info.get("size", most_used_font_size)
                                    line_fname = line_info.get("fontname", most_used_font_name)
                                    is_bold_line = (
                                        line_fname != most_used_font_name
                                        and (
                                            "bold" in line_fname.lower()
                                            or line_fname in bold_font_names
                                        )
                                    ) or line_size > most_used_font_size + 0.4

                                    if is_list:
                                        # List item: flush accumulator, emit list item riêng
                                        flush_accumulator()
                                        merged_lines.append({"text": cleaned, "is_header": False})
                                    elif is_bold_line:
                                        if current_acc_is_header:
                                            # Tiếp tục gộp các dòng bold liên tiếp (wrap của cùng 1 heading)
                                            current_accumulator.append(cleaned)
                                        else:
                                            # Flush paragraph hiện tại, bắt đầu header mới
                                            flush_accumulator()
                                            current_accumulator.append(cleaned)
                                            current_acc_is_header = True
                                    else:
                                        if current_acc_is_header:
                                            # Gặp dòng thường sau header → flush header, bắt đầu paragraph mới
                                            flush_accumulator()
                                            current_acc_is_header = False
                                            current_accumulator.append(cleaned)
                                        else:
                                            # Tiếp tục gộp paragraph
                                            if current_accumulator:
                                                last_line = current_accumulator[-1]
                                                ends_with_punc = last_line[-1] in (".", "!", "?", ":") if last_line else False
                                                starts_with_lower = cleaned[0].islower() if cleaned else False
                                                if not ends_with_punc or starts_with_lower:
                                                    current_accumulator.append(cleaned)
                                                else:
                                                    flush_accumulator()
                                                    current_accumulator.append(cleaned)
                                            else:
                                                current_accumulator.append(cleaned)

                                flush_accumulator()

                                for entry in merged_lines:
                                    line_text = entry["text"]
                                    # Tra cứu font info thực tế của dòng (sau khi merge)
                                    line_info = line_font_info.get(line_text.strip())
                                    if not line_info:
                                        for key, val in line_font_info.items():
                                            if line_text.strip().startswith(key) or key in line_text.strip():
                                                line_info = val
                                                break
                                    line_size = line_info.get("size", most_used_font_size) if line_info else most_used_font_size
                                    line_fname = line_info.get("fontname", most_used_font_name) if line_info else most_used_font_name
                                    block_type = self._determine_block_type_by_font(
                                        line_text, line_size, line_fname,
                                        most_used_font_size, max_font_size,
                                        most_used_font_name, bold_font_names
                                    )
                                    extracted_blocks.append(
                                        DocumentBlock(
                                            block_type=block_type,
                                            bbox=BoundingBox(0.0, band["y1"], float(page.width), band["y2"]),
                                            content=line_text
                                        )
                                    )

                    elif band["type"] == "exclusion":
                        # Trích xuất cấu trúc bảng biểu và hình ảnh
                        sorted_elements = sorted(
                            band["elements"], 
                            key=lambda e: e["data"].bbox[0] if e["type"] == "table" else e["data"]["x0"]
                        )
                        for el in sorted_elements:
                            if el["type"] == "table":
                                table = el["data"]
                                raw_table_data = table.extract()
                                if raw_table_data:
                                    extracted_blocks.append(
                                        DocumentBlock(
                                            block_type=BlockType.TABLE,
                                            bbox=BoundingBox(*table.bbox),
                                            content=self._convert_table_to_markdown(raw_table_data)
                                        )
                                    )
                            elif el["type"] == "image" and image_output_dir:
                                os.makedirs(image_output_dir, exist_ok=True)
                                img = el["data"]
                                image_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                                image_name = f"page_{page_idx + 1}_img_{len(extracted_blocks) + 1}.png"
                                image_path = os.path.join(image_output_dir, image_name)
                                try:
                                    page.crop(image_bbox).to_image(resolution=150).save(image_path)
                                    extracted_blocks.append(
                                        DocumentBlock(
                                            block_type=BlockType.IMAGE,
                                            bbox=BoundingBox(*image_bbox),
                                            content=image_path
                                        )
                                    )
                                except Exception as e:
                                    logger.warning(f"Không thể trích xuất cấu trúc ảnh tại {image_path}: {e}")

        return self.sorter.sort_blocks(extracted_blocks)


class LocalCoreEngine:
    def __init__(self):
        self.sorter = DocumentLayoutSorter()
        self.pdf_parser = LocalPDFParser(self.sorter)

    def extract_markdown_string(self, pdf_path: str, output_dir: Optional[str] = None) -> str:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Không tìm thấy tệp tin PDF mục tiêu: {pdf_path}")
            
        document_ast = self.pdf_parser.parse(pdf_path, output_dir=output_dir)
        return MarkdownCompiler.compile(document_ast)

    def convert_pdf_to_markdown(self, pdf_path: str, output_md_path: str) -> None:
        logger.info(f"Bắt đầu quá trình trích xuất và lưu trữ file: {pdf_path}")
        
        output_dir = os.path.dirname(output_md_path) or "."
        os.makedirs(output_dir, exist_ok=True)
            
        markdown_result = self.extract_markdown_string(pdf_path, output_dir=output_dir)
        
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_result)
            
        logger.info(f"Quá trình đồng bộ cấu trúc file vật lý hoàn tất: {output_md_path}")


@register(".pdf")
def pdf_to_markdown(file_path: str | Path, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    base_name = Path(file_path).stem
    output_md_path = os.path.join(output_dir, f"{base_name}.md")
    
    engine = LocalCoreEngine()
    markdown_result = engine.extract_markdown_string(str(file_path), output_dir=output_dir)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_result)
        
    return markdown_result


if __name__ == "__main__":
    test_pdf = "document.pdf"
    output_file = "output.md"

    if os.path.exists(test_pdf):
        core_engine = LocalCoreEngine()
        core_engine.convert_pdf_to_markdown(test_pdf, output_file)
    else:
        logger.warning(
            f"Hệ thống không tìm thấy tệp tin mẫu '{test_pdf}' nhằm mục đích khởi chạy thử nghiệm."
        )