from __future__ import annotations

import os
import time

from fileconcat.config import (
    AppConfig,
    ScanStats,
    DEFAULT_EXCLUDED_DIR_NAMES,
    DEFAULT_BINARY_EXTS,
)
from .matchers import make_path_matchers, make_content_matcher
from . import tui


def iter_files(root: str, recursive: bool):
    """
    Iterate over files, working with path strings.
    When performing a recursive traversal, exclude directories with names
    in DEFAULT_EXCLUDED_DIR_NAMES.
    """
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # exclude non-necessary directories on the fly,
            # so that os.walk doesn't enter them at all
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDED_DIR_NAMES]
            for name in filenames:
                yield os.path.join(dirpath, name)
    else:
        with os.scandir(root) as it:
            for entry in it:
                if entry.is_file():
                    yield entry.path


def scan_files(cfg: AppConfig) -> tuple[list[tuple[str, str]], ScanStats]:
    """
    Обходит файловую систему и возвращает:
      - список (file_path_str, rel_path_str)
      - статистику сканирования
    """
    input_dir_str = str(cfg.input_dir)
    output_file_str = str(cfg.output_file)

    include_path, exclude_path = make_path_matchers(
        cfg.pattern,
        cfg.exclude_pattern,
        cfg.match_mode,
    )
    content_matcher = make_content_matcher(
        cfg.content_pattern,
        cfg.content_exclude_pattern,
        cfg.match_mode,
        cfg.batch_size,
        DEFAULT_BINARY_EXTS,
    )

    stats = ScanStats()
    filtered: list[tuple[str, str]] = []

    scan_start = time.monotonic()
    last_scan_update = scan_start

    for file_path_str in iter_files(input_dir_str, recursive=cfg.recursive):
        stats.scanned += 1

        now = time.monotonic()
        if now - last_scan_update >= .1:
            elapsed = now - scan_start
            tui.update_scan_progress(stats.scanned, elapsed)
            last_scan_update = now

        if file_path_str == output_file_str:
            continue

        rel_path_str = os.path.relpath(file_path_str, input_dir_str).replace(os.sep, "/")
        name = os.path.basename(file_path_str)

        # path include / exclude
        if cfg.pattern and not include_path(rel_path_str, name):
            continue
        if cfg.exclude_pattern and exclude_path(rel_path_str, name):
            continue

        # content-based filters
        include_ok, excluded, had_warning = content_matcher.check(file_path_str, name)
        if had_warning:
            tui.print_warning(rel_path_str)

        if not include_ok or excluded:
            continue

        filtered.append((file_path_str, rel_path_str))

    stats.matched = len(filtered)
    stats.scan_elapsed = time.monotonic() - scan_start

    tui.print_scan_summary(stats)
    return filtered, stats
