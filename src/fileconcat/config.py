from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VERSION = "2.0.0"

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

DEFAULT_BATCH_SIZE = 100

MatchMode = Literal["exact", "substring", "regex"]


@dataclass
class AppConfig:
    input_dir: Path
    output_file: Path
    no_body: bool
    no_headers: bool
    pattern: str | None
    match_mode: MatchMode
    exclude_pattern: str | None
    recursive: bool
    content_pattern: str | None
    content_exclude_pattern: str | None
    batch_size: int


@dataclass
class ScanStats:
    scanned: int = 0
    matched: int = 0
    scan_elapsed: float = 0.0
