# HANDOFF — 2026-02-20

## Цель сессии
Создать систему управления аккаунтами для ООО Шоппилайф: структурный документ + Excalidraw-схема с 3 аккаунтами + скилл `/excalidraw-diagram`.

## Сделано
- [x] `Projects/Система аккаунтов/Первая версия.md` — структурированный документ системы аккаунтов
- [x] Excalidraw-схема: 3 зоны (ISO/RDP-A/RDP-B), 3 аккаунта, внутренние коммуникации, KeePassXC
- [x] Исправлена схема: groupIds (зоны + блоки двигаются вместе), startBinding/endBinding (стрелки прилипают), L-shape для диагональной стрелки, bound labels на дуговой стрелке
- [x] Скилл `/excalidraw-diagram` создан: `~/.claude/skills/` (глобально) + `.claude/skills/excalidraw-diagram/SKILL.md` (в проекте)

## Текущее состояние
- Последняя схема: https://excalidraw.com/#json=r4ZMz5i9Gy8USo74tI1BB,nlDsNir76LvXReSkZh04JQ
- Незакоммичено: `.claude/skills/excalidraw-diagram/SKILL.md`, `Projects/Система аккаунтов/`, HANDOFF.md
- Staged (предыдущая сессия): research-guide.md, social-research skills, Scripts/

## Что решили и почему
- `export_to_excalidraw` вместо `create_view` — только export правильно сохраняет текст
- Arrow labels через `containerId: "arrow_id"` — floating text не прилипает к стрелке
- `opacity: 100` + светлый `backgroundColor` — иначе `opacity: 40` делает zone label прозрачным

## Что НЕ пробовать
- `label` shorthand в export JSON — работает только в streaming (`create_view`), не в файловом формате
- `opacity: 40` на zone backgrounds — делает zone label полупрозрачным
- MCP tools внутри Task sub-агентов — не передаются (только главная сессия)

## Следующие шаги
1. `git add .claude/skills/excalidraw-diagram/ "Projects/Система аккаунтов/" HANDOFF.md && git commit && git push`
2. Настройка реальной ячейки ООО Шоппилайф (чеклист в Первая версия.md)
3. Создать шаблон для тиражирования на другие юрлица

## Важные файлы
- `Projects/Система аккаунтов/Первая версия.md` — документ системы
- `.claude/skills/excalidraw-diagram/SKILL.md` — скилл (шаблоны, чеклист, типичные ошибки)

## Справка
- Последний коммит: 629dd1d feat(skills): add global python-project-init, contract-first, handoff skills
- Тесты: n/a (не затронуты этой сессией)
