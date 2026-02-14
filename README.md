# ClaudeCode

Рабочее пространство для работы с [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — CLI-инструментом от Anthropic. Содержит настройки, кастомные команды и утилиты для повседневной разработки с помощью AI.

## Возможности

### Slash-команды

Набор кастомных команд для ускорения рабочего процесса:

| Команда | Описание |
|---------|----------|
| `/commit` | Анализирует изменения и создаёт коммит в формате [Conventional Commits](https://www.conventionalcommits.org/) |
| `/review` | Код-ревью: баги, безопасность, производительность, качество кода |
| `/test` | Запуск тестов, анализ падений и предложение фиксов |
| `/explain [target]` | Объяснение кода, функции или структуры проекта |
| `/refactor [target]` | Рефакторинг с сохранением поведения |

Команды находятся в `.claude/commands/` и автоматически подхватываются Claude Code.

### Swarm Mode

Скрипты для запуска Claude Code в многоагентном (swarm) режиме:

- `claude-swarm.bat` — запуск из CMD
- `claude-swarm.ps1` — запуск из PowerShell

## Структура проекта

```
ClaudeCode/
├── .claude/
│   ├── commands/          # Кастомные slash-команды
│   │   ├── commit.md
│   │   ├── review.md
│   │   ├── test.md
│   │   ├── explain.md
│   │   └── refactor.md
│   └── settings.local.json
├── CLAUDE.md              # Инструкции для Claude Code
├── claude-swarm.bat       # Swarm mode (CMD)
├── claude-swarm.ps1       # Swarm mode (PowerShell)
└── README.md
```

## Быстрый старт

1. Установите [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
2. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/silveriumX/ClaudeCode.git
   cd ClaudeCode
   ```
3. Запустите Claude Code:
   ```bash
   claude
   ```
4. Используйте кастомные команды: `/commit`, `/review`, `/test`, `/explain`, `/refactor`

## Добавление своих команд

Создайте `.md` файл в `.claude/commands/`:

```markdown
# .claude/commands/my-command.md
Описание того, что должна делать команда.
Поддерживается $ARGUMENTS для передачи аргументов.
```

После этого команда `/my-command` станет доступна в Claude Code.

## Лицензия

MIT
