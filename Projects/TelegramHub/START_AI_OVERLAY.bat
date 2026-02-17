@echo off
chcp 65001 >nul
echo ============================================================
echo   AI Overlay dlya AyuGram
echo ============================================================
echo.
echo [*] Zapusk...
echo.
echo 1. Otkroyte chat v AyuGram
echo 2. Vydelite tekst myshkoy (zazhmi i provedi)
echo 3. Nazhmite F9 - tekst skopiruetsya i AI predlozhit otvet
echo.

cd /d "%~dp0"
python ai_overlay_ayugram.py

pause
