"""
Скрипт очистки архивной папки _archive
Удаляет 80% файлов, оставляет только самые важные
"""
import os
import shutil

base_path = r"C:\Users\Admin\Documents\Cursor\Projects\FinanceBot\_archive"

print("=== ОЧИСТКА _archive ===\n")

# 1. Удалить все setup_scripts (структура таблицы уже настроена)
setup_scripts = os.path.join(base_path, "setup_scripts")
if os.path.exists(setup_scripts):
    shutil.rmtree(setup_scripts)
    print("✓ Удалено: setup_scripts/")

# 2. Удалить почти все deploy_docs (оставить только LATEST)
deploy_docs = os.path.join(base_path, "deploy_docs")
if os.path.exists(deploy_docs):
    # Переименовать DEPLOY_REPORT_29_01_2026.md в LATEST.md
    latest_file = os.path.join(deploy_docs, "DEPLOY_REPORT_29_01_2026.md")
    if os.path.exists(latest_file):
        shutil.copy(latest_file, os.path.join(deploy_docs, "LATEST.md"))

    # Удалить все остальные файлы
    for file in os.listdir(deploy_docs):
        if file != "LATEST.md":
            os.remove(os.path.join(deploy_docs, file))
    print("✓ Очищено: deploy_docs/ (оставлен LATEST.md)")

# 3. Удалить старые тесты
test_scripts = os.path.join(base_path, "test_scripts")
if os.path.exists(test_scripts):
    # Оставить только TEST_REPORT_FINAL.md
    for file in os.listdir(test_scripts):
        if file.endswith('.py') or (file.endswith('.md') and 'FINAL' not in file):
            file_path = os.path.join(test_scripts, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    print("✓ Очищено: test_scripts/ (оставлен TEST_REPORT_FINAL.md)")

# 4. Очистить 80% reports (оставить самые важные)
reports = os.path.join(base_path, "reports")
if os.path.exists(reports):
    # Файлы которые нужно оставить
    keep_files = [
        "FINAL_STRUCTURE.md",
        "TABLE_VS_BOT_LOGIC_AUDIT.md",
        "SYSTEM_READY.md",
        "IMPLEMENTATION_PLAN_FINANCE_SYSTEM.md",
        "UNIFIED_SHEETS_STRUCTURE.md"
    ]

    deleted_count = 0
    for file in os.listdir(reports):
        if file not in keep_files and os.path.isfile(os.path.join(reports, file)):
            os.remove(os.path.join(reports, file))
            deleted_count += 1

    print(f"✓ Очищено: reports/ (удалено {deleted_count} файлов, оставлено {len(keep_files)})")

# 5. Удалить deploy_scripts (старые скрипты)
deploy_scripts = os.path.join(base_path, "deploy_scripts")
if os.path.exists(deploy_scripts):
    shutil.rmtree(deploy_scripts)
    print("✓ Удалено: deploy_scripts/")

print("\n=== ОЧИСТКА ЗАВЕРШЕНА ===")
print(f"Папка _archive теперь содержит только необходимые файлы")
