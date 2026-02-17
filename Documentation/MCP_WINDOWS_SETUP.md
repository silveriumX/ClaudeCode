# MCP Windows Filesystem Server - Установка

## Что установлено

MCP (Model Context Protocol) сервер для работы с файловой системой Windows через Cursor AI.

## Установленные компоненты

### 1. NPM пакет
```powershell
npm install -g @modelcontextprotocol/server-filesystem
```

**Версия:** 2026.1.14
**Расположение:** `C:\Users\Admin\AppData\Roaming\npm\node_modules\@modelcontextprotocol\server-filesystem`

### 2. Конфигурационные файлы

#### Глобальная конфигурация
**Файл:** `C:\Users\Admin\.cursor\mcp.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\Admin",
        "C:\\Users\\Admin\\Documents\\Cursor"
      ],
      "env": {}
    }
  }
}
```

#### Локальная конфигурация (для текущего проекта)
**Файл:** `C:\Users\Admin\Documents\Cursor\.cursor\mcp.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "${workspaceFolder}",
        "${userHome}"
      ],
      "env": {}
    }
  }
}
```

## Возможности MCP Filesystem Server

### Инструменты (Tools)
- `read_file` - чтение содержимого файла
- `read_multiple_files` - чтение нескольких файлов
- `write_file` - запись в файл
- `create_directory` - создание директории
- `list_directory` - список файлов в директории
- `move_file` - перемещение файла
- `search_files` - поиск файлов
- `get_file_info` - получение метаданных файла
- `list_allowed_directories` - список разрешённых директорий

### Доступные директории
- **Глобально:** `C:\Users\Admin` и `C:\Users\Admin\Documents\Cursor`
- **В проекте:** Корень проекта и домашняя директория пользователя

## Как использовать

### После установки

1. **Перезапустите Cursor IDE**
2. **Проверьте доступность MCP сервера:**
   - Откройте чат с AI
   - Посмотрите в раздел "Available Tools"
   - Там должны появиться инструменты MCP filesystem

### Примеры использования в чате

```
Прочитай файл C:\Users\Admin\Documents\test.txt используя MCP

Создай директорию C:\Users\Admin\Projects\NewProject

Найди все Python файлы в C:\Users\Admin\Documents\Cursor
```

### Включение/отключение инструментов

В интерфейсе чата Cursor можно:
- Кликнуть на название инструмента в списке "Available Tools" чтобы включить/отключить его
- Отключенные инструменты не будут загружаться в контекст

### Автоматическое выполнение (Auto-run)

По умолчанию AI будет спрашивать разрешение перед использованием MCP инструментов.

Чтобы включить автоматическое выполнение без запроса:
- Настройки Cursor → Agent → Auto-run → включить для MCP tools

## Безопасность

⚠️ **Важно:** MCP сервер имеет доступ только к указанным директориям:
- `C:\Users\Admin`
- `C:\Users\Admin\Documents\Cursor`

Для доступа к другим директориям нужно добавить их в конфигурацию `mcp.json`.

## Обновление

```powershell
npm update -g @modelcontextprotocol/server-filesystem
```

## Отладка

### Проверка работы сервера
```powershell
npx -y @modelcontextprotocol/server-filesystem "C:\Users\Admin"
```

### Логи MCP в Cursor
Логи находятся в:
```
C:\Users\Admin\AppData\Roaming\Cursor\logs\[дата]\window1\exthost\anysphere.cursor-mcp\MCP Logs.log
```

## Дополнительные MCP серверы

Можно установить и другие MCP серверы, добавив их в `mcp.json`:

### Пример: добавление другого сервера
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${workspaceFolder}"]
    },
    "another-server": {
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "API_KEY": "${env:MY_API_KEY}"
      }
    }
  }
}
```

## Полезные ссылки

- [Официальная документация Cursor MCP](https://cursor.com/docs/context/mcp)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [GitHub репозиторий MCP servers](https://github.com/modelcontextprotocol/servers)

## Дата установки

24 января 2026
