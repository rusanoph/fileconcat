from __future__ import annotations

import os
import time
import random
from pathlib import Path

from fileconcat.config import AppConfig, ScanStats, VERSION
from fileconcat.banner import BANNERS

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RED = "\033[31m"
CYAN = "\033[36m"


def _supports_color() -> bool:
    return os.name != "nt" or "WT_SESSION" in os.environ or "ANSICON" in os.environ


_USE_COLOR = _supports_color()


def _c(code: str) -> str:
    return code if _USE_COLOR else ""

def get_random_banner() -> str:
    return random.choice(BANNERS)

def print_banner() -> None:
    text = rf"""
{get_random_banner()}{RESET}
             {BOLD}fileconcat {VERSION}{RESET}
""".strip("\n")
    print(text.replace(BOLD, _c(BOLD)).replace(RESET, _c(RESET)))


def print_config_summary(cfg: AppConfig) -> None:
    print()
    print(f"{_c(BOLD)}Input directory:{_c(RESET)} {cfg.input_dir}")
    print(f"{_c(BOLD)}Output file:    {_c(RESET)} {cfg.output_file}")
    print(f"{_c(BOLD)}Recursive:      {_c(RESET)} {cfg.recursive}")
    print(f"{_c(BOLD)}Headers, Body:  {_c(RESET)} {not cfg.no_headers}, {not cfg.no_body}")
    print(
        f"{_c(BOLD)}Path pattern:   {_c(RESET)} {cfg.pattern!r}, "
        f"exclude: {cfg.exclude_pattern!r}, mode: {cfg.match_mode}"
    )
    print(
        f"{_c(BOLD)}Content pattern:{_c(RESET)} {cfg.content_pattern!r}, "
        f"exclude: {cfg.content_exclude_pattern!r}"
    )
    print(f"{_c(BOLD)}Batch size:     {_c(RESET)} {cfg.batch_size} lines")
    print()


def update_scan_progress(scanned: int, elapsed: float) -> None:
    msg = f"{_c(YELLOW)}Scanning...{_c(RESET)} scanned {scanned} files (elapsed {elapsed:.1f}s)"
    print(msg, end="\r", flush=True)


def print_scan_summary(stats: ScanStats) -> None:
    print()
    print(
        f"{_c(CYAN)}Scan finished:{_c(RESET)} "
        f"scanned {stats.scanned} files, matched {stats.matched}, "
        f"in {stats.scan_elapsed:.1f}s."
    )
    print()


def print_warning(path_str: str, error: Exception | None = None) -> None:
    if error is not None:
        print(
            f"{_c(RED)}Warning:{_c(RESET)} could not read file {path_str}: {error}"
        )
    else:
        print(
            f"{_c(RED)}Warning:{_c(RESET)} could not read file {path_str}"
        )


def _progress_bar(processed: int, total: int, start_time: float, width: int = 40) -> str:
    if total <= 0:
        return ""
    ratio = processed / total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    percent = ratio * 100
    elapsed = time.monotonic() - start_time
    return f"[{bar}] {processed}/{total} ({percent:5.1f}%) | {elapsed:6.1f}s"


def print_write_progress(processed: int, total: int, start_time: float) -> None:
    bar = _progress_bar(processed, total, start_time)
    print(bar, end="\r", flush=True)


def print_no_matches(stats: ScanStats) -> None:
    print()
    print(
        f"{_c(YELLOW)}No files matched the given criteria.{_c(RESET)} "
        f"(scanned {stats.scanned} files in {stats.scan_elapsed:.1f}s)"
    )


def print_done(
    stats: ScanStats,
    write_elapsed: float,
    total_elapsed: float,
    output_file: Path,
) -> None:
    size_str = "unknown"
    try:
        size = output_file.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                size_str = f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
                break
            size /= 1024
    except Exception:
        pass

    print()
    print(
        f"{_c(GREEN)}Done.{_c(RESET)} "
        f"Scan: {stats.scan_elapsed:.1f}s, write: {write_elapsed:.1f}s, total: {total_elapsed:.1f}s."
    )
    print(
        f"Matched files: {stats.matched}, "
        f"output: {output_file} ({size_str})"
    )
