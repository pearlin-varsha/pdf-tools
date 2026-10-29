"""
pdfops.py - things you do TO PDFs: merge, compress, split/extract, pages to images.

Uses PyMuPDF (imported as "pymupdf"), a fast library for reading and writing PDFs.
"""

from pathlib import Path

import pymupdf

from common import (IMAGE_EXTENSIONS, PDF_EXTENSIONS, check_files, human_size,
                    natural_key, report_errors, unique_path)
from convert import image_to_pdf_bytes


def _open_pdf(src):
    """Open a PDF, refusing password-protected ones with a clear message."""
    doc = pymupdf.open(src)
    if doc.needs_pass:
        doc.close()
        raise ValueError("it's password-protected")
    return doc


# --------------------------------------------------------------------------
# Merge
# --------------------------------------------------------------------------

def run_merge(paths):
    """Combine every selected image/PDF into one 'Merged.pdf', sorted by file name."""
    files, errors = check_files(paths, IMAGE_EXTENSIONS | PDF_EXTENSIONS)
    if errors:                                           # don't make a half-merged file
        return report_errors(errors)
    if len(files) < 2:
        return report_errors([], "Select two or more files to merge.")

    files.sort(key=natural_key)                          # Screenshot (2) before Screenshot (10)
    merged = pymupdf.open()                              # a new, empty PDF
    for src in files:
        try:
            if src.suffix.lower() in IMAGE_EXTENSIONS:
                part = pymupdf.open("pdf", image_to_pdf_bytes(src))  # image -> 1-page PDF in memory
            else:
                part = _open_pdf(src)
            merged.insert_pdf(part)                      # append all its pages to the end
            part.close()
        except Exception as exc:
            errors.append(f"{src.name}: {exc}")
    if errors:
        merged.close()
        return report_errors(errors)

    out = unique_path(files[0].parent / "Merged.pdf")    # saved next to the first file
    merged.save(out, garbage=3, deflate=True)            # garbage/deflate = tidy up and shrink
    merged.close()
    return 0


# --------------------------------------------------------------------------
# Compress
# --------------------------------------------------------------------------

def _compress_one(src):
    """Compress one PDF. Returns (old size, new size, output path or None)."""
    doc = _open_pdf(src)
    if hasattr(doc, "rewrite_images"):                   # needs PyMuPDF 1.26+
        # Big photos/scans are what make PDFs huge. Shrink any image sharper than
        # 200 dpi down to 150 dpi (still crisp on screen and when printed) and
        # re-save it as JPEG quality 70.
        doc.rewrite_images(dpi_threshold=200, dpi_target=150, quality=70)
    out = unique_path(src.with_name(f"{src.stem}_compressed.pdf"))
    # garbage=4: drop unused/duplicate objects; deflate: zip-compress everything; clean: tidy page code
    doc.save(out, garbage=4, deflate=True, clean=True)
    doc.close()

    old_size, new_size = src.stat().st_size, out.stat().st_size
    if new_size >= old_size:                             # no gain: don't leave a useless copy
        out.unlink()
        return old_size, old_size, None
    return old_size, new_size, out


def run_compress(paths):
    """'Compress PDF': makes name_compressed.pdf and shows how much was saved."""
    files, errors = check_files(paths, PDF_EXTENSIONS)
    lines = []
    for src in files:
        try:
            old, new, out = _compress_one(src)
            if out:
                saved = 100 - new * 100 // old
                lines.append(f"{src.name}: {human_size(old)} -> {human_size(new)} ({saved}% smaller)")
            else:
                lines.append(f"{src.name}: already as small as it gets ({human_size(old)})")
        except Exception as exc:
            errors.append(f"{src.name}: {exc}")
    return report_errors(errors, "\n".join(lines) if lines else None)


# --------------------------------------------------------------------------
# Split / extract pages
# --------------------------------------------------------------------------

def parse_page_ranges(text, page_count):
    """'1-3, 5' -> [0, 1, 2, 4]  (page numbers start at 0 inside PyMuPDF).

    Raises ValueError with a readable message if the text is wrong.
    """
    pages = []
    for part in text.replace(" ", "").split(","):        # "1-3,5" -> ["1-3", "5"]
        if not part:
            continue
        try:
            if "-" in part:
                start, end = (int(x) for x in part.split("-", 1))
            else:
                start = end = int(part)
        except ValueError:
            raise ValueError(f"'{part}' isn't a page number or range like 2-5")
        if not (1 <= start <= end <= page_count):
            raise ValueError(f"'{part}' is outside 1-{page_count}")
        pages.extend(range(start - 1, end))              # convert to 0-based
    if not pages:
        raise ValueError("enter at least one page, e.g. 1-3, 5")
    return pages


def extract_pages(src, pages, label):
    """Save the chosen pages as a new PDF. Returns its path."""
    doc = _open_pdf(src)
    new = pymupdf.open()
    for i in pages:
        new.insert_pdf(doc, from_page=i, to_page=i)      # copy one page at a time, in the order asked
    safe_label = label.replace(" ", "").replace(",", "_")   # "1-3, 5" -> "1-3_5" for the file name
    out = unique_path(src.with_name(f"{src.stem}_pages_{safe_label}.pdf"))
    new.save(out, garbage=3, deflate=True)
    new.close()
    doc.close()
    return out


def split_all_pages(src):
    """Save every page as its own PDF inside a new folder. Returns the folder."""
    doc = _open_pdf(src)
    folder = unique_path(src.with_name(f"{src.stem}_pages"))
    folder.mkdir()
    width = len(str(doc.page_count))                     # 120 pages -> 3 digits: p001, p002, ...
    for i in range(doc.page_count):
        single = pymupdf.open()
        single.insert_pdf(doc, from_page=i, to_page=i)
        single.save(folder / f"{src.stem}_p{i + 1:0{width}d}.pdf", garbage=3, deflate=True)
        single.close()
    doc.close()
    return folder


def run_split(paths):
    """'Split / extract pages': asks what you want in a small window, then does it."""
    from dialogs import ask_split_options                # imported here: only this feature needs a window
    files, errors = check_files(paths, PDF_EXTENSIONS)
    for src in files:
        try:
            with _open_pdf(src) as doc:
                page_count = doc.page_count
            choice = ask_split_options(src.name, page_count)
            if choice is None:                           # user pressed Cancel / closed the window
                continue
            mode, text = choice
            if mode == "split":
                split_all_pages(src)
            else:
                extract_pages(src, parse_page_ranges(text, page_count), text)
        except Exception as exc:
            errors.append(f"{src.name}: {exc}")
    return report_errors(errors)


# --------------------------------------------------------------------------
# PDF pages -> images
# --------------------------------------------------------------------------

def run_pdf2img(paths, dpi=150):
    """'Convert pages to images': one PNG per page in a new folder next to the PDF."""
    files, errors = check_files(paths, PDF_EXTENSIONS)
    for src in files:
        try:
            doc = _open_pdf(src)
            folder = unique_path(src.with_name(f"{src.stem}_images"))
            folder.mkdir()
            width = len(str(doc.page_count))
            for i, page in enumerate(doc, start=1):      # enumerate gives (1, page1), (2, page2), ...
                pix = page.get_pixmap(dpi=dpi)           # draw the page as a picture
                pix.save(folder / f"{src.stem}_p{i:0{width}d}.png")
            doc.close()
        except Exception as exc:
            errors.append(f"{src.name}: {exc}")
    return report_errors(errors)
