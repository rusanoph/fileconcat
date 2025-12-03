# FileConcat

Small fast CLI tool to recursively gather multiple files into a single text file.

Useful when you need to:

- create a "snapshot" of project code for review or sharing
- feed code / configs into LLMs / analysis tools
- quickly search relevant files by *path* and/or *content*
- generate a textual "map" of a project

---

## Features

- 🔁 **Recursive or flat** directory scanning (`-r` flag)
- 🧭 **Path filtering**:
  - `-p/--pattern` — include only paths matching pattern
  - `-x/--exclude-pattern` — exclude paths matching pattern
  - `-m exact|substring|regex` — how to interpret patterns
- 📄 **Content filtering**:
  - `-P/--content-pattern` — include only files whose content matches pattern
  - `-X/--content-exclude-pattern` — drop files if content matches pattern
  - substring or regex matching, with batched reading for speed
- 🧠 **Smart defaults**:
  - skips heavy folders like `node_modules`, `.git`, `dist`, `build`, etc.
  - skips obvious binary files when searching by content (images, archives, fonts, etc.)
- 🖥 **Nice TUI**:
  - ASCII banner
  - progress bar with percentage and elapsed time
  - scan summary and final stats

---

## Output format

Resulting file is a concatenation of selected files in the form:

```text
# path/to/file1.ext
<file1 contents>

# other/dir/file2.txt
<file2 contents>

...
```

You can control whether to write:

- headers only (`-B/--no-body`)
- body only (`-H/--no-headers`)
- or both (default).


## Usage

General usage:
```bash
fileconcat -i <input_dir> -o <output_file> [options...]
```

Основные параметры

- -i, --in — input directory (required)

- -o, --out — output file (required)

- -r, --recursive — recursive traversal of subdirectories (only top-level files by default)

- -B, --no-body — do not write file contents, only headers

- -H, --no-headers — do not write headers, only file contents

- -p, --pattern — include pattern for path

- -x, --exclude-pattern — exclude pattern for path

- -m, --match-mode — matching mode for -p/-x/-P/-X:

	- exact (default) — exact match of path or file name

	- substring — substring in path or file name

	- regex — regular expression (Python re)

- -P, --content-pattern — include pattern for file content

- -X, --content-exclude-pattern — exclude pattern for file content

- --batch-size — how many lines to read at a time when searching by content (default 100)

### Use cases
1. Collect all code from src into one file
```bash
fileconcat -i ./src -o ./all_src.txt -r
```

To use:
- apply to the task/directory;
- build an LLM from the entire project code.

2. List only files (without content)
```bash
fileconcat -i . -o project_files.txt -r -B
```


Result:
```text
# src/main.py

# src/utils/helpers.py

# tests/test_main.py
...
```

Can be used as a "project snapshot".

3. Filtering by path using regex

For example, only .py from src/main:
```bash
fileconcat \
  -i . \
  -o src_main_py.txt \
  -r \
  -p 'src/main/.*\.py' \
  -m regex
```

4. Search by content: only files containing "handler"
```bash
fileconcat \
  -i . \
  -o handler_files.txt \
  -r \
  -P 'handler' \
  -m substring
```

Includes only files where the content contains "handler" (case-insensitive; with -m regex, complex patterns can be used).

5. Exclude files where "DEBUG" is present (logging)
```bash
fileconcat \
  -i ./src \
  -o no_debug.txt \
  -r \
  -X 'DEBUG' \
  -m substring
```

6. Combination: path + content

For example, take only files under src, where the path contains handler, and inside contains SUCCESS, but not ERROR:

fileconcat \
  -i . \
  -o src_handler_success.txt \
  -r \
  -p 'src.*[Hh]andler' \
  -m regex \
  -P 'SUCCESS' \
  -X 'ERROR' \
  -m substring

## Performance notes

- Scanning a large repository (100k+ files) heavily depends on disk speed.

- Tool:

	- automatically skips directories: `node_modules`, `.git`, `.idea`, `.vscode`, `dist`, `build`, `out`, `venv`, `__pycache__`, ...

	- does not read binary files when searching by content: `.jpg/.png`, `.zip/.jar`, `.exe`, `.class`, `fonts`, etc.

- Real-time numbers depend on the hardware, but a typical run with smart filters takes around ~1 second for 100k+ files.

## 📄 License

MIT — see [LICENSE](./LICENSE).