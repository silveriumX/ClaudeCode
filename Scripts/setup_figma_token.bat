@echo off
chcp 65001 >nul
echo ========================================
echo Figma Token Setup
echo ========================================
echo.
echo Этот скрипт поможет добавить Figma токен в .env
echo.
echo Инструкция:
echo 1. Откройте https://www.figma.com/settings
echo 2. Account → Personal access tokens
echo 3. Create a new personal access token
echo 4. Скопируйте токен (начинается с figd_)
echo 5. Вставьте сюда
echo.
echo ========================================
echo.

set /p TOKEN="Вставьте ваш Figma токен: "

if "%TOKEN%"=="" (
    echo.
    echo ❌ Токен пустой!
    echo.
    pause
    exit /b 1
)

if not "%TOKEN:~0,5%"=="figd_" (
    echo.
    echo ⚠️  Предупреждение: токен не начинается с 'figd_'
    echo Вы уверены что скопировали правильный токен?
    echo.
    set /p CONFIRM="Продолжить? (y/n): "
    if /i not "%CONFIRM%"=="y" (
        echo Отменено
        pause
        exit /b 1
    )
)

cd /d "%~dp0\.."

powershell -Command "(Get-Content .env) -replace 'FIGMA_API_TOKEN=.*', 'FIGMA_API_TOKEN=%TOKEN%' | Set-Content .env"

echo.
echo ✓ Токен добавлен в .env
echo.
echo Проверка подключения...
echo.

cd Scripts
python figma_connect.py

echo.
echo ========================================
pause
