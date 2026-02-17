@echo off
echo ========================================
echo Testing Figma API Connection
echo ========================================
echo.

cd /d "%~dp0"
python figma_connect.py

echo.
echo ========================================
pause
