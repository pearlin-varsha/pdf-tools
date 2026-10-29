"""
convert.py - turning images and Office files into PDFs.
"""

import io                          # in-memory "files"
import shutil                      # find programs on PATH, move files
import subprocess                  # run LibreOffice as a separate program
import tempfile                    # temporary folder for LibreOffice output
from pathlib import Path

import img2pdf                     # lossless image -> PDF
from PIL import Image              # Pillow: open/fix images

from common import (IMAGE_EXTENSIONS, OFFICE_EXTENSIONS, WORD_EXTENSIONS,
                    POWERPOINT_EXTENSIONS, EXCEL_EXTENSIONS,
                    check_files, report_errors, unique_path)

# Formats img2pdf can embed as-is. Others (BMP, WebP) get converted to PNG first.
IMG2PDF_NATIVE = {"JPEG", "PNG", "TIFF", "GIF", "JPEG2000", "MPO"}


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------

def _has_transparency(img):
    """True if the image has see-through parts, which img2pdf refuses."""
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _flatten_to_png_bytes(img):
    """Place the image on white and return it as lossless PNG bytes."""
    rgba = img.convert("RGBA")
    background = Image.new("RGB", rgba.size, "white")
    background.paste(rgba, mask=rgba.getchannel("A"))  # alpha channel decides what shows through
    buffer = io.BytesIO()
    background.save(buffer, format="PNG")
    return buffer.getvalue()


def image_to_pdf_bytes(src):
    """Return the PDF (as bytes in memory) for one image. Merge reuses this."""
    with Image.open(src) as img:
        if _has_transparency(img) or img.format not in IMG2PDF_NATIVE:
            data = _flatten_to_png_bytes(img)
        else:
            data = Path(src).read_bytes()                # untouched original = zero quality loss
    # ifvalid = turn phone photos upright using the camera's rotation tag
    return img2pdf.convert(data, rotation=img2pdf.Rotation.ifvalid)


def run_img2pdf(paths):
    """'Convert to PDF' on images: one PDF next to each image."""
    files, errors = check_files(paths, IMAGE_EXTENSIONS)
    for src in files:
        try:
            unique_path(src.with_suffix(".pdf")).write_bytes(image_to_pdf_bytes(src))
        except Exception as exc:
            errors.append(f"{src.name}: {exc}")
    return report_errors(errors)                         # silent on success; the PDF just appears


# --------------------------------------------------------------------------
# Office (Word, PowerPoint, Excel)
# --------------------------------------------------------------------------
# Plan A: use Microsoft Office itself (best-looking result) through "COM", the
#         Windows system that lets one program remote-control another.
# Plan B: if Office isn't installed, use free LibreOffice in "headless" mode
#         (no window).
# Plan C: neither installed -> tell the user what to install.

def _convert_with_ms_office(files, errors):
    """Convert with Word / PowerPoint / Excel. Returns files it could NOT handle."""
    try:
        import pythoncom                                 # part of pywin32 (Windows only)
        import win32com.client
    except ImportError:
        return files                                     # not on Windows / pywin32 missing: Plan B

    pythoncom.CoInitialize()                             # required before using COM in a program
    leftover = []

    # Group files by which Office app opens them, so each app starts only once.
    groups = [
        ("Word.Application", WORD_EXTENSIONS),
        ("PowerPoint.Application", POWERPOINT_EXTENSIONS),
        ("Excel.Application", EXCEL_EXTENSIONS),
    ]
    for app_name, extensions in groups:
        group = [f for f in files if f.suffix.lower() in extensions]
        if not group:
            continue
        try:
            # DispatchEx = start a NEW hidden copy, so we never disturb documents you have open
            app = win32com.client.DispatchEx(app_name)
        except Exception:
            leftover.extend(group)                       # this app isn't installed: try Plan B
            continue
        try:
            for src in group:
                out = unique_path(src.with_suffix(".pdf"))
                try:
                    if app_name == "Word.Application":
                        app.Visible = False
                        app.DisplayAlerts = 0
                        doc = app.Documents.Open(str(src), ReadOnly=True, AddToRecentFiles=False,
                                                 ConfirmConversions=False)
                        doc.ExportAsFixedFormat(str(out), 17)        # 17 = PDF
                        doc.Close(False)                             # False = don't save changes
                    elif app_name == "PowerPoint.Application":
                        pres = app.Presentations.Open(str(src), ReadOnly=True, Untitled=False,
                                                      WithWindow=False)
                        pres.SaveAs(str(out), 32)                    # 32 = PDF
                        pres.Close()
                    else:
                        app.Visible = False
                        app.DisplayAlerts = False
                        book = app.Workbooks.Open(str(src), ReadOnly=True)
                        book.ExportAsFixedFormat(0, str(out))        # 0 = PDF
                        book.Close(False)
                except Exception as exc:
                    errors.append(f"{src.name}: {exc}")
        finally:
            app.Quit()                                   # always close the hidden app, even after errors
    return leftover


def _find_libreoffice():
    """Return the path to LibreOffice's soffice program, or None."""
    candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return shutil.which("soffice")                       # also works on Linux/Mac for testing


def _convert_with_libreoffice(files, errors):
    """Convert with LibreOffice. Returns files it could NOT handle."""
    soffice = _find_libreoffice()
    if not soffice:
        return files
    for src in files:
        # LibreOffice always names the output "<name>.pdf" and would overwrite an existing
        # one, so we let it write into a temporary folder, then move it to a safe name.
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(src)],
                capture_output=True, timeout=180,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # no black window on Windows
            )
            produced = Path(tmp) / (src.stem + ".pdf")
            if produced.is_file():
                shutil.move(str(produced), str(unique_path(src.with_suffix(".pdf"))))
            else:
                errors.append(f"{src.name}: LibreOffice couldn't convert it "
                              f"({result.stderr.decode(errors='ignore').strip()[:200]})")
    return []


def run_office2pdf(paths):
    """'Convert to PDF' on Word/PowerPoint/Excel files."""
    files, errors = check_files(paths, OFFICE_EXTENSIONS)
    leftover = _convert_with_ms_office(files, errors)          # Plan A
    leftover = _convert_with_libreoffice(leftover, errors)     # Plan B
    for src in leftover:                                       # Plan C
        errors.append(f"{src.name}: needs Microsoft Office or the free LibreOffice "
                      f"(libreoffice.org) to convert")
    return report_errors(errors)
