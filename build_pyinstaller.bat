@echo off
REM Author: Ozy
REM PyInstaller Build Script for StarLogs

echo ========================================
echo Building StarLogs with PyInstaller
echo ========================================
echo.

REM Clean previous build
if exist "dist\pyinstaller" (
    echo Cleaning previous PyInstaller build...
    rmdir /s /q dist\pyinstaller
)
if exist "build\build_starlogs" (
    rmdir /s /q build\build_starlogs
)

echo.
echo Starting PyInstaller compilation (onefile)...
echo This will take 2-3 minutes...
echo.

"venv\Scripts\python.exe" -m PyInstaller ^
    --onefile ^
    --console ^
    --name StarLogs ^
    --distpath dist\pyinstaller ^
    --workpath build\build_starlogs ^
    --add-data "static;static" ^
    --add-data "templates;templates" ^
    --hidden-import=flask ^
    --hidden-import=psutil ^
    --hidden-import=rich ^
    --hidden-import=win32file ^
    --hidden-import=win32con ^
    --hidden-import=pywintypes ^
    --collect-all flask ^
    --collect-all jinja2 ^
    --collect-all markupsafe ^
    --icon=static/favicon.ico ^
    --noconfirm ^
    starlogs.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Successful!
echo ========================================
echo.
echo Executable location: dist\pyinstaller\StarLogs.exe
echo.

REM Test the executable
echo Testing executable...
"dist\pyinstaller\StarLogs.exe" --help

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Build verification PASSED!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Build verification FAILED!
    echo ========================================
)

echo.
pause


