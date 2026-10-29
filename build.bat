@echo off
REM ------------------------------------------------------------------
REM  Turns pdftools.py into a Windows app in dist\PDFTools\
REM  Run this from the pdf-tools folder:   build.bat
REM ------------------------------------------------------------------

REM Install the libraries the app uses, plus PyInstaller (the packager)
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

REM --onedir    : a folder of files instead of one big exe. Starts much faster,
REM               which matters because it launches on every right-click.
REM --noconsole : no black terminal window flashing up.
REM --noconfirm : overwrite the previous build without asking.
REM --name      : the exe will be called PDFTools.exe
python -m PyInstaller --onedir --noconsole --noconfirm --name PDFTools pdftools.py
if errorlevel 1 goto :fail

echo.
echo Build finished: dist\PDFTools\PDFTools.exe
echo Next: open installer.iss in Inno Setup and press Compile (Ctrl+F9).
goto :eof

:fail
echo.
echo Build FAILED - read the error above.
exit /b 1
