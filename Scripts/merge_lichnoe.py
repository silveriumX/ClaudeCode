# -*- coding: utf-8 -*-
"""Скрипт объединения Личное1 в Личное. Запуск из корня репозитория."""
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\Admin\Documents\Cursor")
LICHNOE1 = ROOT / "Личное1"
LICHNOE = ROOT / "Личное"

# Папки для копирования из Личное1 в Личное
FOLDERS = [
    "VoiceNotes",
    "Notes",
    "Здоровье",
    "Уход_за_кожей",
    "Психология_и_ментальное",
    "Стиль_и_внешность",
    "Идеи_и_желания",
    "Рисование",
]

# Файлы в корне Личное1 -> корень Личное
ROOT_FILES = ["CONTEXT_INDEX.md", "LIFE_CONTEXT_SYSTEM.md", "ЛИЧНАЯ_ОПЕРАЦИОНКА.md"]

def main():
    for folder in FOLDERS:
        src = LICHNOE1 / folder
        dst = LICHNOE / folder
        if not src.exists():
            print(f"Skip (no source): {folder}")
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.name == "18.01. ночные заметки о ночи.md" and folder == "Психология_и_ментальное":
                if f.stat().st_size == 0:
                    print(f"Skip empty duplicate: {f.name}")
                    continue
            dest_file = dst / f.name
            if f.is_file():
                shutil.copy2(f, dest_file)
                print(f"Copy: {folder}/{f.name}")
            else:
                shutil.copytree(f, dest_file, dirs_exist_ok=True)
                print(f"Copy dir: {folder}/{f.name}")

    for name in ROOT_FILES:
        src = LICHNOE1 / name
        if src.exists():
            shutil.copy2(src, LICHNOE / name)
            print(f"Copy root: {name}")

    # Перенос файлов из корня Личное в подпапки
    psych_root = [
        "Психопортрет_24_01_2026.md",
        "Уточнение_Реальных_Проблем.md",
        "САМОЕ_ВАЖНОЕ_Действуй_Сегодня.md",
        "Game_Changers_и_Ключевые_Выводы.md",
        "Неочевидные_Советы_Которые_Работают.md",
        "Практический_Гайд_Найти_Своих.md",
        "ПРОДВИНУТЫЕ_ТЕХНИКИ.md",
        "ШПАРГАЛКА.md",
        "СИСТЕМА_РАБОТЫ.md",
    ]
    for name in psych_root:
        f = LICHNOE / name
        if f.exists():
            shutil.move(str(f), str(LICHNOE / "Психология_и_ментальное" / name))
            print(f"Move to Психология: {name}")

    # Дневниковые в Notes (18.01 с контентом — переименовать в .md)
    night = LICHNOE / "18.01. ночные заметки о ночи"
    if night.exists():
        dest = LICHNOE / "Notes" / "18.01. ночные заметки о ночи.md"
        shutil.copy2(night, dest)
        night.unlink()
        print("Move to Notes: 18.01. ночные заметки о ночи -> 18.01. ночные заметки о ночи.md")
    for name in ["30.01. канал", "Диалог от 24.01", "Как воспринимать мелкие действия"]:
        f = LICHNOE / name
        if f.exists():
            shutil.move(str(f), str(LICHNOE / "Notes" / name))
            print(f"Move to Notes: {name}")
    # 30.01. диалог с клод — не переносим (дубликат по INDEX)
    dialog30 = LICHNOE / "30.01. диалог с клод"
    if dialog30.exists():
        (LICHNOE / "Notes").mkdir(parents=True, exist_ok=True)
        shutil.move(str(dialog30), str(LICHNOE / "Notes" / "30.01. диалог с клод"))
        print("Move to Notes: 30.01. диалог с клод (на проверку)")

    print("Done.")

if __name__ == "__main__":
    main()
