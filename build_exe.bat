@echo off
REM Build bboxfixer-gui.exe using PyInstaller
REM Run this script from the repository root on Windows.
REM
REM Requirements:
REM   pip install pyinstaller
REM
REM Output: dist\bboxfixer-gui.exe

echo === BBoxFixer GUI – EXE Builder ===
echo.

python -m pyinstaller bboxfixer-gui.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed. Make sure pyinstaller is installed:
    echo   pip install pyinstaller
    exit /b %errorlevel%
)

echo.
echo Build complete.
echo Executable: dist\bboxfixer-gui.exe
echo.
