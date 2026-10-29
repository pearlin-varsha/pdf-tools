"""
common.py - small helpers every feature uses.
"""

import re                          # regular expressions: used to split names into text and number parts
import sys                         # to check whether we're running on Windows
from pathlib import Path           # friendly file-path handling

APP_NAME = "PDF Tools"

# Which file types each feature accepts. Keep in sync with make_installer.py.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
WORD_EXTENSIONS = {".doc", ".docx", ".rtf", ".odt"}
POWERPOINT_EXTENSIONS = {".ppt", ".pptx", ".odp"}
EXCEL_EXTENSIONS = {".xls", ".xlsx", ".ods"}
OFFICE_EXTENSIONS = WORD_EXTENSIONS | POWERPOINT_EXTENSIONS | EXCEL_EXTENSIONS   # "|" = combine sets
PDF_EXTENSIONS = {".pdf"}


def show_message(text, is_error=False):
    """Pop-up box on Windows, terminal print elsewhere.

    The exe has no console window, so a pop-up is the only way to talk to the user.
    """
    if sys.platform == "win32":
        import ctypes                                   # lets Python call Windows' own functions
        icon = 0x10 if is_error else 0x40               # 0x10 = red X, 0x40 = blue "i"
        topmost = 0x40000                               # keep the box in front of Explorer
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, icon | topmost)
    else:
        print(f"{APP_NAME}: {text}", file=sys.stderr if is_error else sys.stdout)


def report_errors(errors, done_text=None):
    """Show one pop-up listing every problem, or an optional success note.

    Returns the exit code: 1 if anything failed, 0 if all went well.
    """
    if errors:
        show_message("Some files could not be processed:\n\n" + "\n".join(errors), is_error=True)
        return 1
    if done_text:
        show_message(done_text)
    return 0


def unique_path(path):
    """Return `path` if free, else 'name (1).ext', 'name (2).ext', ...

    Works for folders too. Means we never overwrite anything the user already has.
    """
    path = Path(path)
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def natural_key(path):
    """Sort key so 'Screenshot (2)' comes before 'Screenshot (10)'.

    Normal sorting compares text letter by letter, so "10" < "2" (because "1" < "2").
    We split the name into text and number chunks and compare numbers as numbers:
    "Screenshot (10).png" -> ["screenshot (", 10, ").png"]
    """
    parts = re.split(r"(\d+)", Path(path).name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def human_size(num_bytes):
    """1536000 -> '1.5 MB'. For friendly messages."""
    for unit in ("bytes", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.0f} {unit}" if unit == "bytes" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024


def check_files(paths, allowed_extensions):
    """Split paths into (good Path objects, error messages) based on existence and type."""
    good, errors = [], []
    for p in paths:
        src = Path(p)
        if not src.is_file():
            errors.append(f"{src.name}: file not found")
        elif src.suffix.lower() not in allowed_extensions:
            errors.append(f"{src.name}: this file type isn't supported here")
        else:
            good.append(src.resolve())                 # resolve() = full absolute path (Office needs this)
    return good, errors
