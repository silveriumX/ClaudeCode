@echo off
chcp 65001 >nul
title DocChat - Запуск

echo ========================================
echo    📄 DocChat - Локальный ассистент
echo ========================================
echo.

cd /d "%~dp0"

echo Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo Активация venv...
    call venv\Scripts\activate.bat
) else (
    echo Используется системный Python
)

echo.
echo Запуск приложения...
echo Откройте в браузере: http://localhost:8501
echo.
echo Для остановки нажмите Ctrl+C
echo ========================================
echo.

streamlit run app.py --server.headless true

pause
