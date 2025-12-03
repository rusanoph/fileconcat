import argparse
import os
from pathlib import Path
import re

VERSION = "1.2.0"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Recursively gather all files from a directory into one file."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"fileconcat {VERSION}",
        help="show the version and exit",
    )
    parser.add_argument(
        "-i", "--in",
        dest="input_dir",
        required=True,
        help="input directory from which to read files recursively",
    )
    parser.add_argument(
        "-o", "--out",
        dest="output_file",
        required=True,
        help="path to the resulting file",
    )
    parser.add_argument(
        "-B", "--no-body",
        dest="no_body",
        action="store_true",
        help="don't include body in the output file",
    )
    parser.add_argument(
        "-H", "--no-headers",
        dest="no_headers",
        action="store_true",
        help="don't include file headers in the output file",
    )
    parser.add_argument(
        "-p", "--pattern",
        dest="pattern",
        help=(
            "Filter files by relative path or name. "
            "Example (regex): '.*config.*/.*\\.txt', "
            "example (exact): 'dir/file.txt'"
        ),
    )
    parser.add_argument(
        "-m", "--match-mode",
        dest="match_mode",
        choices=["regex", "exact"],
        default="exact",
        help="How to interpret --pattern: 'exact' (default) or 'regex'.",
    )
    parser.add_argument(
        "-x", "--exclude-pattern",
        dest="exclude_pattern",
        help=(
            "Exclude files whose relative path or name matches this pattern. "
            "Interpreted according to --match-mode."
        ),
    )
    parser.add_argument(
        "-r", "--recursive",
        dest="recursive",
        action="store_true",
        help="Recurse into subdirectories. If not set, only top-level files in --in are processed.",
    )
    return parser.parse_args()


def iter_files(root: Path, recursive: bool):
    """Iterate over files in root. If recursive is False, only top-level files."""
    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                yield Path(dirpath) / name
    else:
        for entry in root.iterdir():
            if entry.is_file():
                yield entry


def main():
    args = parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_file = Path(args.output_file).resolve()
    no_headers = args.no_headers
    no_body = args.no_body
    pattern = args.pattern
    match_mode = args.match_mode
    exclude_pattern = args.exclude_pattern
    recursive = args.recursive

    print(f"fileconcat version {VERSION}")
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Recursive: {recursive}")
    print(f"No headers: {no_headers}, No body: {no_body}")
    print(f"Pattern: {pattern!r}, exclude: {exclude_pattern!r}, match mode: {match_mode}")

    if no_headers and no_body:
        raise ValueError("Both --no-headers and --no-body cannot be set at the same time.")

    if not input_dir.is_dir():
        raise ValueError(f"--in should point to a directory, not a file: {input_dir}")

    # Подготовим regex-ы при необходимости
    include_regex = None
    exclude_regex = None
    if pattern and match_mode == "regex":
        try:
            include_regex = re.compile(pattern)
        except re.error as e:
            raise SystemExit(f"Invalid regex in --pattern: {e}")
    if exclude_pattern and match_mode == "regex":
        try:
            exclude_regex = re.compile(exclude_pattern)
        except re.error as e:
            raise SystemExit(f"Invalid regex in --exclude-pattern: {e}")

    # Все кандидаты (для расчёта прогресса)
    all_files = list(iter_files(input_dir, recursive=recursive))

    # Фильтрация + относительные пути
    filtered = []
    for file_path in all_files:
        file_path = file_path.resolve()

        # пропускаем сам результирующий файл, если он внутри input_dir
        if file_path == output_file:
            continue

        rel_path = file_path.relative_to(input_dir)
        rel_path_str = rel_path.as_posix()  # "dir/file.ext"

        # include-фильтр
        if pattern:
            if match_mode == "regex":
                if not include_regex.search(rel_path_str):
                    continue
            else:  # exact
                if rel_path_str != pattern and rel_path.name != pattern:
                    continue

        # exclude-фильтр
        if exclude_pattern:
            if match_mode == "regex":
                if exclude_regex.search(rel_path_str):
                    continue
            else:  # exact
                if rel_path_str == exclude_pattern or rel_path.name == exclude_pattern:
                    continue

        filtered.append((file_path, rel_path_str))

    total = len(filtered)
    if total == 0:
        print("No files matched the given criteria. Nothing to do.")
        return

    # Создаём директории под выходной файл, если нужно
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Запись + прогресс
    processed = 0
    with output_file.open("w", encoding="utf-8") as out_f:
        for file_path, rel_path_str in filtered:
            processed += 1

            # Прогресс-бар: "Progress: X/Y files (Z%)"
            percent = processed * 100 // total
            print(f"Progress: {processed}/{total} files ({percent}%)", end="\r", flush=True)

            if not no_headers:
                out_f.write(f"# {rel_path_str}\n")

            if no_body:
                out_f.write("\n")
                continue

            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        out_f.write(line)
            except Exception as e:
                out_f.write(f"[Error reading the file: {e}]\n")

            out_f.write("\n")

    # Перенос строки после прогресса
    print()
    print("Done.")


if __name__ == "__main__":
    main()
