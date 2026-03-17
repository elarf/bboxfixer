@echo off
REM Build bboxfixer-gui.exe using PyInstaller
REM Run this script from the repository root on Windows.
REM Output: dist\bboxfixer-gui.exe

echo === BBoxFixer GUI – EXE Builder ===
echo.

echo Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies.
    exit /b %errorlevel%
)
echo.

echo Building executable...
python -m pyinstaller bboxfixer-gui.spec --clean --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed.
    exit /b %errorlevel%
)

echo.
echo Build complete.
echo Executable: dist\bboxfixer-gui.exe
echo.
