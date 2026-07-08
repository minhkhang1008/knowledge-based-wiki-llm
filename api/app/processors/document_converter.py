import argparse
from pathlib import Path
from .converter_registry import get_converter, REGISTRY
print(REGISTRY)
def convert_file(input_path, output_dir=None):
    source = Path(input_path).resolve()

    if not source.is_file():
        raise FileNotFoundError(source)

    converter = get_converter(source.suffix)

    if not converter:
        raise ValueError(f"Không hỗ trợ: {source.suffix}")

    markdown = converter(source)

    destination_dir = Path(output_dir).resolve() if output_dir else source.parent
    destination_dir.mkdir(parents=True, exist_ok=True)

    output_path = destination_dir / f"{source.stem}.md"
    output_path.write_text(markdown, encoding="utf-8")

    return output_path

def convert_path(input_path: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    """
    Chuyển một file hoặc toàn bộ file hỗ trợ trong thư mục sang Markdown.
    """
    source = Path(input_path).resolve()
    results: list[Path] = []

    if source.is_file():
        return [convert_file(source, output_dir)]

    if not source.is_dir():
        raise FileNotFoundError(f"Không tìm thấy file/thư mục: {source}")

    target_dir = Path(output_dir).resolve() if output_dir else source
    target_dir.mkdir(parents=True, exist_ok=True)

    for file_path in sorted(source.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in REGISTRY:
            relative = file_path.relative_to(source)
            nested_output = target_dir / relative.parent
            results.append(convert_file(file_path, nested_output))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chuyển các file tài liệu được hỗ trợ sang Markdown cho pipeline wiki LLM."
    )
    parser.add_argument(
        "input",
        help="Đường dẫn file hoặc thư mục chứa các file cần chuyển.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Thư mục lưu file Markdown. Mặc định: cùng thư mục với file nguồn.",
    )
    args = parser.parse_args()

    converted = convert_path(args.input, args.output)
    if not converted:
        print("Không có file nào được xử lý.")
        return

    print(f"Đã chuyển {len(converted)} file:")
    for path in converted:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
