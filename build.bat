@echo off
REM Author: Ozy
REM Build script for StarLogs

echo Building StarLogs...
pyinstaller --clean build_starlogs.spec

echo.
echo Build complete! StarLogs.exe is in the dist folder.
echo.
pause

