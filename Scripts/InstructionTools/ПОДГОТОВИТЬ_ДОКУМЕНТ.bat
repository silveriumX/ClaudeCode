@echo off
chcp 65001 > nul
echo.
echo ================================================
echo   Подготовка документа для Cursor
echo ================================================
echo.

if "%~1"=="" (
    echo Перетащите PDF или DOCX файл на этот скрипт!
    echo.
    echo Или запустите из командной строки:
    echo   ПОДГОТОВИТЬ_ДОКУМЕНТ.bat "путь\к\файлу.pdf"
    echo.
    pause
    exit /b
)

echo Обрабатываю: %~nx1
echo.

cd /d "%~dp0"
python prepare_document.py "%~1"

echo.
echo ================================================
echo.
pause
