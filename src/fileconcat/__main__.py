from __future__ import annotations

from fileconcat.cli import parse_args
from fileconcat import tui
from fileconcat.scan import scan_files
from fileconcat.io_write import write_output


def main() -> None:
    cfg = parse_args()

    tui.print_banner()
    tui.print_config_summary(cfg)

    files, stats = scan_files(cfg)
    if not files:
        tui.print_no_matches(stats)
        return

    write_elapsed = write_output(cfg, files)
    total_elapsed = stats.scan_elapsed + write_elapsed

    tui.print_done(stats, write_elapsed, total_elapsed, cfg.output_file)


if __name__ == "__main__":
    main()
