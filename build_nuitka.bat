@echo off
REM Author: Ozy
REM Nuitka Build Script for StarLogs

echo ========================================
echo Building StarLogs with Nuitka
echo ========================================
echo.

REM Clean previous build
if exist "dist\nuitka" (
    echo Cleaning previous Nuitka build...
    rmdir /s /q dist\nuitka
)
if exist "build\build_nuitka" (
    rmdir /s /q build\build_nuitka
)

echo.
echo Starting Nuitka compilation...
echo This will take 5-10 minutes on first build...
echo.

"venv\Scripts\python.exe" -m nuitka ^
    --standalone ^
    --assume-yes-for-downloads ^
    --windows-console-mode=force ^
    --enable-plugin=anti-bloat ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=setuptools ^
    --nofollow-import-to=distutils ^
    --include-data-dir=static=static ^
    --include-data-dir=templates=templates ^
    --include-package=flask ^
    --include-package=psutil ^
    --include-package=rich ^
    --jobs=32 ^
    --output-filename=StarLogs.exe ^
    --output-dir=build\build_nuitka ^
    --company-name=Ozy311 ^
    --product-name=StarLogs ^
    --file-version=0.8.3 ^
    --product-version=0.8.3 ^
    --file-description="Star Citizen Log Monitor and Analyzer" ^
    starlogs.py

REM Move the output to dist\nuitka
if not exist "dist\nuitka" mkdir dist\nuitka
xcopy /E /I /Y "build\build_nuitka\starlogs.dist\*" "dist\nuitka\"

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
echo Executable location: dist\nuitka\StarLogs.exe
echo.

REM Test the executable
echo Testing executable...
"dist\nuitka\StarLogs.exe" --help

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


