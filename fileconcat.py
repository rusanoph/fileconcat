import argparse
import os
from pathlib import Path
import re
import time

VERSION = "1.3.1"


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
        choices=["regex", "exact"],
        default="exact",
        help="How to interpret patterns: 'exact' (default) or 'regex'.",
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
            "(regex or exact substring, see --match-mode)."
        ),
    )
    parser.add_argument(
        "-X", "--content-exclude-pattern",
        dest="content_exclude_pattern",
        help=(
            "Exclude files whose *content* matches this pattern "
            "(regex or exact substring, see --match-mode)."
        ),
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
    output_file = Path(args.output_file).resolve()
    no_headers = args.no_headers
    no_body = args.no_body
    pattern = args.pattern
    match_mode = args.match_mode
    exclude_pattern = args.exclude_pattern
    recursive = args.recursive
    content_pattern = args.content_pattern
    content_exclude_pattern = args.content_exclude_pattern

    print(f"fileconcat version {VERSION}")
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Recursive: {recursive}")
    print(f"No headers: {no_headers}, No body: {no_body}")
    print(f"Path pattern: {pattern!r}, exclude: {exclude_pattern!r}, match mode: {match_mode}")
    print(f"Content pattern: {content_pattern!r}, content exclude: {content_exclude_pattern!r}")

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
    filtered = []

    for file_path in iter_files(input_dir, recursive=recursive):
        scanned += 1

        now = time.monotonic()
        if now - last_scan_update >= 0.1:
            elapsed = now - scan_start
            print(
                f"Scanning files... scanned {scanned} files (elapsed {elapsed:.1f}s)",
                end="\r",
                flush=True,
            )
            last_scan_update = now

        # file_path уже абсолютный, потому что input_dir был resolve()
        if file_path == output_file:
            continue

        rel_path = file_path.relative_to(input_dir)
        rel_path_str = rel_path.as_posix()  # "dir/file.ext"

        # Path include filter
        if pattern:
            if match_mode == "regex":
                if not include_regex.search(rel_path_str):
                    continue
            else:  # exact
                if rel_path_str != pattern and rel_path.name != pattern:
                    continue

        # Path exclude filter
        if exclude_pattern:
            if match_mode == "regex":
                if exclude_regex.search(rel_path_str):
                    continue
            else:  # exact
                if rel_path_str == exclude_pattern or rel_path.name == exclude_pattern:
                    continue

        # Content-based filters (only if any content pattern given)
        if content_pattern or content_exclude_pattern:
            content_matches = False
            content_excluded = False
            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        # include content pattern
                        if content_pattern and not content_matches:
                            if match_mode == "regex":
                                if content_include_regex.search(line):
                                    content_matches = True
                            else:  # exact substring
                                if content_pattern in line:
                                    content_matches = True
                        # exclude content pattern
                        if content_exclude_pattern and not content_excluded:
                            if match_mode == "regex":
                                if content_exclude_regex.search(line):
                                    content_excluded = True
                            else:
                                if content_exclude_pattern in line:
                                    content_excluded = True
                        # early break
                        if content_excluded or (
                            content_pattern and content_matches and not content_exclude_pattern
                        ):
                            break
            except Exception as e:
                print(f"\nWarning: could not read file {rel_path_str}: {e}")
                continue

            if content_pattern and not content_matches:
                continue
            if content_exclude_pattern and content_excluded:
                continue

        filtered.append((file_path, rel_path_str))

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
        for file_path, rel_path_str in filtered:
            processed += 1
            print_progress(processed, total, write_start)

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

    write_elapsed = time.monotonic() - write_start
    total_elapsed = scan_elapsed + write_elapsed

    print()  # newline after progress bar
    print(
        f"Done. Writing took {write_elapsed:.1f}s, "
        f"total time {total_elapsed:.1f}s."
    )


if __name__ == "__main__":
    main()
