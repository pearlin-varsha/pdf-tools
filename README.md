# PDF Tools (v2)

Right-click a file → **PDF Tools ▸** → pick what you want. The submenu only
shows the options that make sense for that file type.

| Right-click on… | Options |
|---|---|
| Images (.jpg .png .bmp .gif .tif .webp) | Convert to PDF · Merge into one PDF |
| Word / PowerPoint / Excel (.docx .pptx .xlsx and older/Open formats) | Convert to PDF |
| PDFs | Merge into one PDF · Compress PDF · Split / extract pages · Convert pages to images |

## What each option does

- **Convert to PDF**: one PDF next to each selected file.
  Office files need Microsoft Office *or* the free LibreOffice installed.
- **Merge into one PDF**: select several images and/or PDFs, right-click one of them,
  choose Merge. Makes `Merged.pdf`, pages in file-name order
  (Screenshot (2) comes before Screenshot (10)). Rename files first to control the order.
- **Compress PDF**: makes `name_compressed.pdf` by shrinking large images to 150 dpi,
  then tells you how much smaller it got. Text-only PDFs may not shrink much.
- **Split / extract pages**: a small window opens. Type pages like `1-3, 5` and press
  *Extract pages* → `name_pages_1-3_5.pdf`. Or press *Split every page* → a folder with
  one PDF per page.
- **Convert pages to images**: a folder with one PNG per page.

Nothing is ever overwritten: if a name is taken you get `name (1).pdf`.

## Files

| File | What it does |
|---|---|
| `pdftools.py` | Entry point: reads the command and runs the right feature |
| `common.py` | Shared helpers: pop-ups, safe file names, natural sorting |
| `collector.py` | Gathers files when several are selected (Windows starts one copy per file) |
| `convert.py` | Images and Office files → PDF |
| `pdfops.py` | Merge, compress, split/extract, pages → images |
| `dialogs.py` | The page-picker window for Split / extract |
| `make_installer.py` | Generates `installer.iss` (only re-run it if you change the menu) |
| `installer.iss` | Inno Setup script that builds the installer and the right-click submenu |
| `build.bat` | Packages everything into `dist\PDFTools\PDFTools.exe` |

## Updating from v1

1. Replace your old files with these (keep the same folder).
2. `pip install -r requirements.txt`
3. Test from the VS Code terminal, e.g.
   `python pdftools.py compress "C:\path\to\file.pdf"`
4. `.\build.bat`
5. Open `installer.iss` **from this folder** in Inno Setup → Ctrl+F9
6. Run `installer_output\PDFTools-Setup-2.0.exe`. It upgrades v1 and replaces the old
   single "Convert to PDF" item with the new submenu.

On Windows 11 the submenu is under **Show more options** (or Shift + right-click).
