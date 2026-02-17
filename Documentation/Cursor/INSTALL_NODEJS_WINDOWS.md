# Установка Node.js на Windows

## Быстрый способ

1. **Скачать установщик LTS (рекомендуется):**
   https://nodejs.org/en/download

   Или прямая ссылка на Windows x64 MSI:
   https://nodejs.org/dist/v24.13.1/node-v24.13.1-x64.msi

2. **Запустить скачанный `.msi`** — следовать шагам мастера.

3. **Важно:** отметить опцию **"Add to PATH"** (обычно включена по умолчанию).

4. **Полностью закрыть Cursor** и запустить снова (чтобы подхватился новый PATH).

5. Проверить в новом терминале:
   ```powershell
   node -v
   npx -v
   ```

После этого MCP‑серверы **fireflies**, **zoom**, **exa**, **google-drive** должны запускаться (если они включены в настройках MCP).

## Если winget доступен

В PowerShell (от имени пользователя):

```powershell
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
```

Затем перезапустить Cursor.
