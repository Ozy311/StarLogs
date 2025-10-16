@echo off
REM Author: Ozy
REM Nuitka Build Script for StarLogs

echo ========================================
echo Building StarLogs with Nuitka
echo ========================================
echo.

REM Clean previous build
if exist "starlogs.dist" (
    echo Cleaning previous Nuitka build...
    rmdir /s /q starlogs.dist
)
if exist "starlogs.build" (
    rmdir /s /q starlogs.build
)
if exist "starlogs.onefile-build" (
    rmdir /s /q starlogs.onefile-build
)

echo.
echo Starting Nuitka compilation...
echo This will take 5-10 minutes on first build...
echo.

"C:\Program Files\Python313\python.exe" -m nuitka ^
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
    --include-package=watchdog ^
    --include-package=rich ^
    --jobs=32 ^
    --output-dir=dist ^
    --company-name=Ozy311 ^
    --product-name=StarLogs ^
    --file-version=0.8.2 ^
    --product-version=0.8.2 ^
    --file-description="Star Citizen Log Monitor and Analyzer" ^
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
echo Executable location: dist\starlogs.dist\StarLogs.exe
echo.

REM Test the executable
echo Testing executable...
"dist\starlogs.dist\StarLogs.exe" --help

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


