"""从纯文本文件导入 AI Reference。

运行默认文件：
    python import_ai_reference.py

单独导入一个新的文件：
    python import_ai_reference.py path/to/new_references.txt

默认会清空旧数据再导入；如需保留旧数据并追加：
    python import_ai_reference.py path/to/new_references.txt --append

新文件中的每条资料都必须使用下面的格式，可连续放置多个区块：

=== AI REFERENCE ===
TITLE: Coping with Disappointing Exam Results
WRITER: Student Minds
SOURCE: https://www.studentminds.org.uk/advice-and-info
PROBLEM_TYPE: academic
CONTENT:
这里填写完整正文，可以包含多个段落。

不要再添加 CHAPTER 或 CHUNK 字段；CONTENT 内的空行和段落会被保留。
SOURCE 填写资料来源的完整网页地址。
PROBLEM_TYPE 只能是 academic、stress、interpersonal、economic 或 other。
"""

# standard library
import argparse
from pathlib import Path

# database
from database import SessionLocal

# database tables
from tables.ai_reference import AIReference


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE_PATH = BASE_DIR / "data" / "coping_topics_en_chunks.txt"
REFERENCE_MARKER = "=== AI REFERENCE ==="
VALID_PROBLEM_TYPES = {"academic", "stress", "interpersonal", "economic", "other"}


def parse_references(text: str) -> list[dict[str, str]]:
    """Parse reference blocks and return the AIReference attributes."""
    references: list[dict[str, str]] = []
    blocks = text.split(REFERENCE_MARKER)

    for block_number, block in enumerate(blocks[1:], start=1):
        block = block.strip()
        if not block:
            continue

        metadata: dict[str, str] = {}
        content_lines: list[str] = []
        reading_content = False

        for line in block.splitlines():
            if reading_content:
                content_lines.append(line)
                continue

            if line == "CONTENT:":
                reading_content = True
                continue

            for field in ("TITLE", "WRITER", "SOURCE", "PROBLEM_TYPE"):
                prefix = f"{field}:"
                if line.startswith(prefix):
                    metadata[field] = line[len(prefix):].strip()
                    break

        reference = {
            "content": "\n".join(content_lines).strip(),
            "title": metadata.get("TITLE", ""),
            "writer": metadata.get("WRITER", ""),
            "source": metadata.get("SOURCE", ""),
            "problem_type": metadata.get("PROBLEM_TYPE", ""),
        }

        missing = [name for name, value in reference.items() if not value]
        if missing:
            raise ValueError(
                f"Reference block {block_number} is missing: {', '.join(missing)}"
            )
        if reference["problem_type"] not in VALID_PROBLEM_TYPES:
            allowed = ", ".join(sorted(VALID_PROBLEM_TYPES))
            raise ValueError(
                f"Reference block {block_number} has invalid PROBLEM_TYPE "
                f"'{reference['problem_type']}'. Allowed values: {allowed}"
            )

        references.append(reference)

    if not references:
        raise ValueError(
            f"No references found. Each entry must start with: {REFERENCE_MARKER}"
        )

    return references


def import_references(file_path: Path, replace_existing: bool = True) -> int:
    """Read one file and import all reference blocks from it."""
    references = parse_references(file_path.read_text(encoding="utf-8"))
    db = SessionLocal()

    try:
        if replace_existing:
            db.query(AIReference).delete(synchronize_session=False)

        db.add_all(AIReference(**reference) for reference in references)
        db.commit()
        return len(references)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import AI reference content.")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=DEFAULT_FILE_PATH,
        help=f"Input text file (default: {DEFAULT_FILE_PATH})",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Keep existing database rows and append the imported references.",
    )
    args = parser.parse_args()

    file_path = args.file.resolve()
    if not file_path.is_file():
        parser.error(f"File does not exist: {file_path}")

    imported_count = import_references(file_path, replace_existing=not args.append)
    action = "appended" if args.append else "imported"
    print(f"Successfully {action} {imported_count} AI references from {file_path}.")


if __name__ == "__main__":
    main()
