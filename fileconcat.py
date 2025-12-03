import argparse
import os
from pathlib import Path
import re
import time

VERSION = "1.5.0"

# Directories that are skipped by default during a recursive traversal
DEFAULT_EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    ".gradle",
    ".mvn",
    ".venv",
    "venv",
}

# Binary file extensions that don't make sense to search for text patterns
DEFAULT_BINARY_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".ico",
    ".pdf",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".jar",
    ".exe", ".dll", ".so", ".dylib",
    ".class",
    ".bin",
    ".woff", ".woff2", ".ttf", ".otf",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gather files from a directory into one file."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"fileconcat {VERSION}",
        help="Show the version and exit",
    )
    parser.add_argument(
        "-i", "--in",
        dest="input_dir",
        required=True,
        help="Input directory from which to read files (optionally recursively)",
    )
    parser.add_argument(
        "-o", "--out",
        dest="output_file",
        required=True,
        help="Path to the resulting file",
    )
    parser.add_argument(
        "-B", "--no-body",
        dest="no_body",
        action="store_true",
        help="If set, only file headers will be written without file contents",
    )
    parser.add_argument(
        "-H", "--no-headers",
        dest="no_headers",
        action="store_true",
        help="If set, only file contents will be written without file headers",
    )
    parser.add_argument(
        "-p", "--pattern",
        dest="pattern",
        help=(
            "Include only files whose relative path or name matches this pattern. "
            "Example (regex): '.*asdf.*/.*\\.txt', example (exact): 'dir/file.txt'"
        ),
    )
    parser.add_argument(
        "-m", "--match-mode",
        dest="match_mode",
        choices=["exact", "substring", "regex"],
        default="exact",
        help="How to interpret patterns: 'exact' (default), 'substring' or 'regex'.",
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
    parser.add_argument(
        "-P", "--content-pattern",
        dest="content_pattern",
        help=(
            "Include only files whose *content* matches this pattern "
            "(regex or substring, see --match-mode). "
            "For 'exact' match-mode this is a substring search."
        ),
    )
    parser.add_argument(
        "-X", "--content-exclude-pattern",
        dest="content_exclude_pattern",
        help=(
            "Exclude files whose *content* matches this pattern "
            "(regex, substring or exact, see --match-mode). "
            "For 'exact' match-mode this is a substring search."
        ),
    )
    parser.add_argument(
        "--batch-size",
        dest="batch_size",
        type=int,
        default=100,
        help="Number of lines to read at once when scanning files for content patterns.",
    )
    return parser.parse_args()


def iter_files(root: str, recursive: bool):
    """
    Iterate over files, working with path strings.
    When performing a recursive traversal, exclude directories with names in DEFAULT_EXCLUDED_DIR_NAMES.
    """
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # exclude non-necessary directories on the fly, so that os.walk doesn't enter them at all
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDED_DIR_NAMES]
            for name in filenames:
                yield os.path.join(dirpath, name)
    else:
        with os.scandir(root) as it:
            for entry in it:
                if entry.is_file():
                    yield entry.path


def print_progress(processed: int, total: int, start_time: float, width: int = 40):
    """Print a progress bar like: [#####-----] 12/100 (12.0%) |  1.2s"""
    if total <= 0:
        return
    ratio = processed / total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    percent = ratio * 100
    elapsed = time.monotonic() - start_time
    print(
        f"[{bar}] {processed}/{total} ({percent:5.1f}%) | {elapsed:6.1f}s",
        end="\r",
        flush=True,
    )


def main():
    args = parse_args()

    input_dir = Path(args.input_dir).resolve()
    input_dir_str = str(input_dir)
    output_file = Path(args.output_file).resolve()
    output_file_str = str(output_file)

    no_headers = args.no_headers
    no_body = args.no_body
    pattern = args.pattern
    match_mode = args.match_mode
    exclude_pattern = args.exclude_pattern
    recursive = args.recursive
    content_pattern = args.content_pattern
    content_exclude_pattern = args.content_exclude_pattern
    batch_size = max(1, args.batch_size)

    print(f"fileconcat version {VERSION}")
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Recursive: {recursive}")
    print(f"Headers: {not no_headers}, body: {not no_body}")
    print(f"Path pattern: {pattern!r}, exclude: {exclude_pattern!r}, match mode: {match_mode}")
    print(f"Content pattern: {content_pattern!r}, content exclude: {content_exclude_pattern!r}")
    print(f"Batch size: {batch_size} lines")

    if no_headers and no_body:
        raise ValueError("Both --no-headers and --no-body cannot be set at the same time.")

    if not input_dir.is_dir():
        raise ValueError(f"--in should point to a directory, not a file: {input_dir}")

    # Compile regexes if needed
    include_regex = None
    exclude_regex = None
    content_include_regex = None
    content_exclude_regex = None

    if pattern and match_mode == "regex":
        include_regex = re.compile(pattern)
    if exclude_pattern and match_mode == "regex":
        exclude_regex = re.compile(exclude_pattern)
    if content_pattern and match_mode == "regex":
        content_include_regex = re.compile(content_pattern)
    if content_exclude_pattern and match_mode == "regex":
        content_exclude_regex = re.compile(content_exclude_pattern)

    # Phase 1: scan files and build filtered list, with time-based progress updates
    scan_start = time.monotonic()
    last_scan_update = scan_start
    scanned = 0
    filtered: list[tuple[str, str]] = []

    for file_path_str in iter_files(input_dir_str, recursive=recursive):
        scanned += 1

        now = time.monotonic()
        if now - last_scan_update >= 1.0:
            elapsed = now - scan_start
            print(
                f"Scanning files... scanned {scanned} files (elapsed {elapsed:.1f}s)",
                end="\r",
                flush=True,
            )
            last_scan_update = now

        if file_path_str == output_file_str:
            continue

        rel_path_str = os.path.relpath(file_path_str, input_dir_str).replace(os.sep, "/")
        name = os.path.basename(file_path_str)

        # Path include filter
        if pattern:
            if match_mode == "regex":
                if not include_regex.search(rel_path_str):
                    continue
            elif match_mode == "substring":
                if pattern not in rel_path_str and pattern not in name:
                    continue
            else:  # exact
                if rel_path_str != pattern and name != pattern:
                    continue

        # Path exclude filter
        if exclude_pattern:
            if match_mode == "regex":
                if exclude_regex.search(rel_path_str):
                    continue
            elif match_mode == "substring":
                if exclude_pattern in rel_path_str or exclude_pattern in name:
                    continue
            else:  # exact
                if rel_path_str == exclude_pattern or name == exclude_pattern:
                    continue

        # Content-based filters (only if any content pattern given)
        if content_pattern or content_exclude_pattern:
            ext = os.path.splitext(name)[1].lower()
            is_binary_like = ext in DEFAULT_BINARY_EXTS

            # If we need to check if a file contains a pattern, and the file has a binary extension —
            # we can immediately skip it: everything is equal, we don't need to read it as text.
            if content_pattern and is_binary_like:
                continue

            content_matches = False
            content_excluded = False

            # If only the exclude pattern is given and the file is binary — consider it as not excluded
            # (since earlier, by the fact, only without unnecessary reading).
            if not is_binary_like:
                try:
                    with open(file_path_str, "r", encoding="utf-8", errors="ignore") as f:
                        batch: list[str] = []

                        def process_batch(batch_text: str) -> bool:
                            """Processes one batch of text. True -> can stop reading the file."""
                            nonlocal content_matches, content_excluded
                            if not batch_text:
                                return False

                            # include content pattern
                            if content_pattern and not content_matches:
                                if match_mode == "regex":
                                    if content_include_regex.search(batch_text):
                                        content_matches = True
                                else:  # exact -> substring
                                    if content_pattern in batch_text:
                                        content_matches = True

                            # exclude content pattern
                            if content_exclude_pattern and not content_excluded:
                                if match_mode == "regex":
                                    if content_exclude_regex.search(batch_text):
                                        content_excluded = True
                                else:  # exact -> substring
                                    if content_exclude_pattern in batch_text:
                                        content_excluded = True

                            # early stop logic
                            if content_excluded:
                                return True
                            if content_pattern and content_matches and not content_exclude_pattern:
                                return True
                            return False

                        for line in f:
                            batch.append(line)
                            if len(batch) >= batch_size:
                                if process_batch("".join(batch)):
                                    break
                                batch = []

                        # process the remaining batch
                        if batch and not (
                            content_excluded or
                            (content_pattern and content_matches and not content_exclude_pattern)
                        ):
                            process_batch("".join(batch))

                except Exception as e:
                    print(f"\nWarning: could not read file {rel_path_str}: {e}")
                    continue

            # final check after content matching
            if content_pattern and not content_matches:
                continue
            if content_exclude_pattern and content_excluded:
                continue

        filtered.append((file_path_str, rel_path_str))

    scan_elapsed = time.monotonic() - scan_start
    print(
        f"\nFound {len(filtered)} matching files out of {scanned} scanned "
        f"in {scan_elapsed:.1f}s."
    )

    total = len(filtered)
    if total == 0:
        print("No files matched the given criteria. Nothing to do.")
        return

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Phase 2: write files with a nice progress bar + elapsed time
    print("Writing output...")
    write_start = time.monotonic()
    processed = 0

    with output_file.open("w", encoding="utf-8") as out_f:
        for file_path_str, rel_path_str in filtered:
            processed += 1
            print_progress(processed, total, write_start)

            if not no_headers:
                out_f.write(f"# {rel_path_str}\n")

            if no_body:
                out_f.write("\n")
                continue

            try:
                with open(file_path_str, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        out_f.write(line)
            except Exception as e:
                out_f.write(f"[Error reading the file: {e}]\n")

            out_f.write("\n")

    write_elapsed = time.monotonic() - write_start
    total_elapsed = scan_elapsed + write_elapsed

    print()  # newline after progress bar
    print(
        f"Done. Writing took {write_elapsed:.1f}s, "
        f"total time {total_elapsed:.1f}s."
    )


if __name__ == "__main__":
    main()
