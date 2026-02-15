# MCP Setup Guide
## Настройка MCP серверов для Research System

---

## 📋 Содержание

1. [EXA Search](#exa-search)
2. [Firecrawl](#firecrawl)
3. [Другие MCP серверы](#другие-mcp-серверы)
4. [Полная конфигурация](#полная-конфигурация)

---

## 🔍 EXA Search

### Получение API ключа

1. Зарегистрируйтесь на https://exa.ai
2. Перейдите в раздел API Keys
3. Создайте новый ключ
4. Скопируйте ключ

### Установка MCP сервера

```bash
npm install -g @modelcontextprotocol/server-exa
```

### Конфигурация

Добавьте в `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-exa"
      ],
      "env": {
        "EXA_API_KEY": "ваш_ключ_здесь"
      }
    }
  }
}
```

### Переменная окружения

Или используйте переменную окружения:

```json
{
  "mcpServers": {
    "exa": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-exa"
      ],
      "env": {
        "EXA_API_KEY": "${env:EXA_API_KEY}"
      }
    }
  }
}
```

И добавьте в `.env`:
```
EXA_API_KEY=ваш_ключ_здесь
```

---

## 🔥 Firecrawl

### Получение API ключа

1. Зарегистрируйтесь на https://firecrawl.dev
2. Перейдите в раздел API
3. Создайте новый ключ
4. Скопируйте ключ

### Установка MCP сервера

```bash
npm install -g @modelcontextprotocol/server-firecrawl
```

### Конфигурация

Добавьте в `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-firecrawl"
      ],
      "env": {
        "FIRECRAWL_API_KEY": "${env:FIRECRAWL_API_KEY}"
      }
    }
  }
}
```

**Примечание:** Firecrawl используется для глубокого парсинга, когда нужен полный контент страницы. Для большинства задач достаточно EXA.

---

## 🌐 Другие MCP серверы

### Google Scholar (если доступен)

```json
{
  "google-scholar": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-google-scholar"],
    "env": {}
  }
}
```

### ArXiv (если доступен)

```json
{
  "arxiv": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-arxiv"],
    "env": {}
  }
}
```

---

## 📝 Полная конфигурация

Пример полной конфигурации `.cursor/mcp.json`:

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
    },
    "document-processor": {
      "command": "python",
      "args": [
        "${workspaceFolder}\\Scripts\\mcp-document-processor\\server.py"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}"
      }
    },
    "exa": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-exa"
      ],
      "env": {
        "EXA_API_KEY": "${env:EXA_API_KEY}"
      }
    },
    "firecrawl": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-firecrawl"
      ],
      "env": {
        "FIRECRAWL_API_KEY": "${env:FIRECRAWL_API_KEY}"
      }
    }
  }
}
```

---

## ✅ Проверка установки

После добавления конфигурации:

1. Перезапустите Cursor
2. Откройте чат с AI
3. Проверьте доступность MCP серверов

Вы можете спросить:
```
Какие MCP серверы доступны?
```

Или попробовать использовать:
```
Используя EXA, найди информацию о "Claude Sonnet 4.5"
```

---

## 🔧 Troubleshooting

### MCP сервер не запускается

1. Проверьте, что Node.js установлен: `node --version`
2. Проверьте, что npm установлен: `npm --version`
3. Проверьте API ключи в `.env`
4. Проверьте логи MCP в Cursor

### API ключ не работает

1. Убедитесь, что ключ скопирован полностью
2. Проверьте, что ключ активен в панели управления сервиса
3. Проверьте лимиты использования API

---

**Последнее обновление:** 28.01.2026
