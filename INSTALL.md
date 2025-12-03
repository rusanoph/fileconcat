# Installation

## 1. From source (Python)

**Requirements:**
- Python 3.11+ (developed with 3.13)
- No third-party dependencies required

Clone the repo:
```bash
git clone https://github.com/rusanoph/fileconcat.git
cd fileconcat
```


### Option A: Run directly with `PYTHONPATH`

Linux/macOS:
```bash
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python -m fileconcat -h
```


Windows (PowerShell):
```powershell
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
python -m fileconcat -h
```


After that, you can use:
```bash
python -m fileconcat -i ./src -o ./all.txt -r
```

### Option B: Build a standalone binary with PyInstaller

Install PyInstaller:
```bash
pip install pyinstaller
```

From the repo root run:
```bash
pyinstaller --onefile -n fileconcat -p src src/fileconcat/__main__.py
```


This will create a binary in the dist/ directory:
- on Linux/macOS: dist/fileconcat
- on Windows: dist/fileconcat.exe

Place the binary in any directory that is in the `PATH`, for example:
- Linux: /usr/local/bin/fileconcat
- Windows: C:\tools\fileconcat\fileconcat.exe

Test:
```bash
fileconcat -h
```

# Installation as a .sh or .bat wrapper (Linux/macOS or Windows)

Add the project root `C:\dev\fileconcat\script` to the `PATH`.

Now you can run fileconcat as a command.


