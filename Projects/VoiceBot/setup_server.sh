#!/bin/bash
# Скрипт установки бота на Ubuntu VPS

# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и pip
sudo apt install python3 python3-pip python3-venv -y

# Создаём папку
mkdir -p ~/voice_bot
cd ~/voice_bot

# Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install aiogram==3.3.0 openai==1.12.0

echo "Установка завершена!"
echo "Теперь:"
echo "1. Скопируй bot.py в ~/voice_bot/"
echo "2. Запусти: cd ~/voice_bot && source venv/bin/activate && python3 bot.py"
