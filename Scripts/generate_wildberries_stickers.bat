@echo off
chcp 65001 >nul
echo ========================================
echo Генератор наклеек для Wildberries
echo ========================================
echo.

cd /d "%~dp0"

echo Создание наклеек...
python create_stickers.py

echo.
echo ========================================
echo Готово!
echo ========================================
echo.
echo Файлы сохранены в: exports\stickers\
echo.
echo - nakleiyka-4sht-green.png (Зелёная, 4 шт)
echo - nakleiyka-6sht-blue.png (Синяя, 6 шт)
echo - nakleiyka-original.png (Оригинал)
echo.
echo Откроем папку с наклейками...
start "" "..\exports\stickers"

pause
