@echo off
chcp 65001 >nul
echo ============================================================
echo   AI Overlay for Telegram
echo ============================================================
echo.
echo 1. Select text in Telegram (Ctrl+C)
echo 2. Press F9 - AI will suggest reply
echo.
echo Keys: 1/2/3 - switch variant, Enter - regenerate
echo ============================================================
echo.

cd /d "%~dp0"
python ai_overlay.py

pause
