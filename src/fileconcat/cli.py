from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import (
    AppConfig,
    MatchMode,
    VERSION,
    DEFAULT_BATCH_SIZE,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fileconcat",
        description="Gather files from a directory into one file.",
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
        help="Input directory from which to read files (optionally recursively).",
    )
    parser.add_argument(
        "-o", "--out",
        dest="output_file",
        required=True,
        help="Path to the resulting file.",
    )
    parser.add_argument(
        "-B", "--no-body",
        dest="no_body",
        action="store_true",
        help="If set, only file headers will be written without file contents.",
    )
    parser.add_argument(
        "-H", "--no-headers",
        dest="no_headers",
        action="store_true",
        help="If set, only file contents will be written without file headers.",
    )
    parser.add_argument(
        "-p", "--pattern",
        dest="pattern",
        help=(
            "Include only files whose relative path or name matches this pattern. "
            "Example (regex): '.*asdf.*/.*\\.txt', example (exact): 'dir/file.txt'."
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
        default=DEFAULT_BATCH_SIZE,
        help="Number of lines to read at once when scanning files for content patterns.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> AppConfig:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir).resolve()
    output_file = Path(args.output_file).resolve()
    match_mode: MatchMode = args.match_mode

    if not input_dir.is_dir():
        raise ValueError(f"--in should point to a directory, not a file: {input_dir}")

    if args.no_headers and args.no_body:
        raise ValueError("Both --no-headers and --no-body cannot be set at the same time.")

    batch_size = max(1, int(args.batch_size))

    return AppConfig(
        input_dir=input_dir,
        output_file=output_file,
        no_body=args.no_body,
        no_headers=args.no_headers,
        pattern=args.pattern,
        match_mode=match_mode,
        exclude_pattern=args.exclude_pattern,
        recursive=bool(args.recursive),
        content_pattern=args.content_pattern,
        content_exclude_pattern=args.content_exclude_pattern,
        batch_size=batch_size,
    )
