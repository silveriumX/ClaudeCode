# Подключение EXA MCP в Claude Code

Инструкция и готовые команды для использования того же EXA MCP, что и в Cursor, в **Claude Code**. Креденшлы взяты из текущей конфигурации Cursor (`.cursor/mcp.json`).

---

## Креденшлы EXA (из этого репозитория)

| Параметр    | Значение |
|------------|----------|
| **EXA_API_KEY** | `7fd68ac8-e98a-416e-9a96-d37fb3d361ac` |

**Важно:** не коммитьте этот ключ в публичные репозитории. Для общих конфигов используйте переменные окружения (см. ниже).

---

## Вариант 1: Remote HTTP (рекомендуется)

Exa предоставляет хостед MCP по адресу `https://mcp.exa.ai/mcp`. Свой API key передаётся через query-параметр.

### Команда в терминале

```bash
claude mcp add --transport http exa "https://mcp.exa.ai/mcp?exaApiKey=7fd68ac8-e98a-416e-9a96-d37fb3d361ac"
```

### Через JSON (add-json)

```bash
claude mcp add-json exa '{"type":"http","url":"https://mcp.exa.ai/mcp?exaApiKey=7fd68ac8-e98a-416e-9a96-d37fb3d361ac"}'
```

### Scope

- Только для текущего проекта (по умолчанию): ключ остаётся в локальной конфигурации.
- Для всех проектов: добавьте `--scope user`.
- Для команды (общий `.mcp.json` в репо): `--scope project` (ключ лучше вынести в `${EXA_API_KEY}`).

---

## Вариант 2: Локальный stdio-сервер (npx exa-mcp-server)

Как в Cursor: запуск `exa-mcp-server` локально с передачей ключа через env.

### Windows (нативный PowerShell/CMD)

На Windows для `npx` нужна обёртка `cmd /c`:

```bash
claude mcp add --transport stdio --env EXA_API_KEY=7fd68ac8-e98a-416e-9a96-d37fb3d361ac exa -- cmd /c npx -y exa-mcp-server
```

### macOS / Linux / WSL

```bash
claude mcp add --transport stdio --env EXA_API_KEY=7fd68ac8-e98a-416e-9a96-d37fb3d361ac exa -- npx -y exa-mcp-server
```

### Запись в `.mcp.json` (project scope, с переменной окружения)

Чтобы не хранить ключ в репозитории, в `.mcp.json` можно использовать подстановку:

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": {
        "EXA_API_KEY": "${EXA_API_KEY}"
      }
    }
  }
}
```

Перед запуском Claude Code задайте переменную (PowerShell):

```powershell
$env:EXA_API_KEY = "7fd68ac8-e98a-416e-9a96-d37fb3d361ac"
```

Или добавьте в профиль пользователя / системные переменные.

---

## Проверка

- Список MCP: `claude mcp list`
- Детали сервера: `claude mcp get exa`
- В чате Claude Code: `/mcp` — проверка статуса и инструментов

---

## Доступные инструменты EXA MCP

После подключения доступны в том числе:

| Инструмент | Описание |
|------------|----------|
| `web_search_exa` | Поиск по вебу, контент готов к использованию |
| `get_code_context_exa` | Поиск кода, документации, примеров (GitHub, Stack Overflow, docs) |
| `company_research_exa` | Исследование компаний: продукты, новости, инсайты |

Опционально можно включить дополнительные инструменты через URL (см. [документацию Exa MCP](https://docs.exa.ai/reference/exa-mcp)).

---

## Промпт для вставки в Claude Code

Скопируй и вставь в Claude Code, если нужно один раз настроить EXA MCP под Windows с моим ключом:

```
Нужно подключить MCP-сервер Exa в Claude Code на Windows с таким API key: 7fd68ac8-e98a-416e-9a96-d37fb3d361ac.

Вариант 1 (предпочтительно): добавь remote HTTP сервер Exa с ключом в URL:
claude mcp add --transport http exa "https://mcp.exa.ai/mcp?exaApiKey=7fd68ac8-e98a-416e-9a96-d37fb3d361ac"

Вариант 2: если нужен локальный stdio-сервер на Windows, используй:
claude mcp add --transport stdio --env EXA_API_KEY=7fd68ac8-e98a-416e-9a96-d37fb3d361ac exa -- cmd /c npx -y exa-mcp-server

После добавления проверь: claude mcp list и claude mcp get exa.
```

Готово: после выполнения одной из команд EXA MCP будет доступен в Claude Code с теми же креденшлами, что и в Cursor.
