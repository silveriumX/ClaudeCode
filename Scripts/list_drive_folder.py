"""
Список файлов в папке Google Drive через Service Account.
Работает с папками, к которым выдали доступ cursor@neat-geode-329707.iam.gserviceaccount.com.

Использование:
  python list_drive_folder.py FOLDER_ID
  или: set GOOGLE_DRIVE_FOLDER_ID=... и python list_drive_folder.py

FOLDER_ID — из URL папки: https://drive.google.com/drive/folders/ЭТОТ_ID
"""
import os
import sys

# Добавляем корень проекта в путь для импорта Utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.google_api import GoogleApiManager


def main():
    folder_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        print("Укажите FOLDER_ID: python list_drive_folder.py FOLDER_ID")
        print("Или задайте GOOGLE_DRIVE_FOLDER_ID в .env")
        sys.exit(1)

    try:
        manager = GoogleApiManager()
        files = manager.list_files_in_folder(folder_id)
        if not files:
            print("Папка пуста или нет доступа.")
            return
        for f in files:
            print(f"{f.get('name', '?')}  (id: {f.get('id')}, type: {f.get('mimeType', '?')})")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
