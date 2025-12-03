from __future__ import annotations

import time

from fileconcat.config import AppConfig
from fileconcat import tui


def write_output(
    cfg: AppConfig,
    files: list[tuple[str, str]],
) -> float:
    """
    Writes a unified file.
    Returns the write time (seconds).
    """
    total = len(files)
    if total == 0:
        return 0.0

    write_start = time.monotonic()
    processed = 0

    cfg.output_file.parent.mkdir(parents=True, exist_ok=True)

    with cfg.output_file.open("w", encoding="utf-8") as out_f:
        for file_path_str, rel_path_str in files:
            processed += 1
            tui.print_write_progress(processed, total, write_start)

            if not cfg.no_headers:
                out_f.write(f"# {rel_path_str}\n")

            if cfg.no_body:
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
    print()  # newline after progress bar
    return write_elapsed
