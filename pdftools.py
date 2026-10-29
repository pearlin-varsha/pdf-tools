"""
PDF Tools - v2
==============
The program the right-click menu runs. Windows calls it like:

    PDFTools.exe <command> "C:\\path\\to\\file"

Commands:
    img2pdf     image(s) -> PDF, one each
    office2pdf  Word / PowerPoint / Excel -> PDF
    merge       several images/PDFs -> one Merged.pdf
    compress    PDF -> smaller PDF
    split       extract chosen pages, or split every page out
    pdf2img     PDF pages -> PNG images

You can test any of them from a terminal, e.g.
    python pdftools.py merge "a.pdf" "b.png"
"""

import sys
import traceback                   # turns a crash into readable text for the error pop-up

import collector
from common import show_message
from convert import run_img2pdf, run_office2pdf
from pdfops import run_compress, run_merge, run_pdf2img, run_split

# command name -> (function that does the work, collector channel or None)
# A channel means "when several files are selected, gather them into ONE run first".
COMMANDS = {
    "img2pdf":    (run_img2pdf, None),        # each image is independent: no gathering needed
    "office2pdf": (run_office2pdf, "office"), # gather so Word opens once, not 10 times
    "merge":      (run_merge, "merge"),       # gather: merge needs every file together
    "compress":   (run_compress, "compress"), # gather: one summary pop-up instead of many
    "split":      (run_split, None),
    "pdf2img":    (run_pdf2img, None),
}


def main():
    args = sys.argv[1:]                                  # drop the program's own name
    if len(args) < 2 or args[0] not in COMMANDS:
        show_message("Usage: PDFTools.exe <command> <file> [more files...]\n\n"
                     "Commands: " + ", ".join(COMMANDS))
        return 1

    command, paths = args[0], args[1:]
    work, channel = COMMANDS[command]

    if channel:
        paths = collector.gather(channel, paths)
        if paths is None:                                # another copy is handling our file
            return 0
    return work(paths)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Without a console, an unexpected crash would just vanish. Show it instead.
        show_message("Something went wrong:\n\n" + traceback.format_exc(limit=3), is_error=True)
        sys.exit(1)
