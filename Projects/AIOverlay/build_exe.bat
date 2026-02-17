@echo off
echo ============================================
echo   Building AI Overlay .exe
echo ============================================
echo.

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Build
echo Building...
pyinstaller --onefile --noconsole --name "AI_Overlay" --icon=icon.ico ai_overlay.py 2>nul
if not exist icon.ico (
    pyinstaller --onefile --noconsole --name "AI_Overlay" ai_overlay.py
)

echo.
echo ============================================
if exist dist\AI_Overlay.exe (
    echo SUCCESS! File: dist\AI_Overlay.exe
    echo.
    echo To share:
    echo 1. Copy dist\AI_Overlay.exe
    echo 2. Copy custom_instructions.txt
    echo 3. User needs to edit API key in the app or use config file
) else (
    echo BUILD FAILED
)
echo ============================================
pause
