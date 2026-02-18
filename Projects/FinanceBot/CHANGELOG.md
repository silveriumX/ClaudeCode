# 📝 FinanceBot - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.6.0] - 2026-02-18

### ✨ Added
- **Initiator notifications** — инициатор заявки теперь получает уведомление об оплате
  отдельно от owner: дата, сумма, получатель/кошелёк, назначение, ссылка на чек
- **Receipt upload via OAuth** — загрузка чеков на Google Drive теперь через OAuth
  (ранее использовался Service Account без квоты хранилища → 403 storageQuotaExceeded)
- **Skill**: `google-drive-oauth-token` — гайд по получению refresh_token для Drive
- **Rule**: `telegram-message-safety.md` — правила безопасного формирования сообщений

### 🔧 Fixed
- **CRITICAL:** Двойные уведомления owner — широкий `try/except` вокруг загрузки + notify
  вызывал второе уведомление при ошибке `reply_text`. Исправлено: узкий except только вокруг upload
- **CRITICAL:** `parse_mode='Markdown'` с Drive URL содержащим `_` → 400 Bad Request → тихая потеря уведомления.
  Исправлено: все уведомления переведены на `parse_mode='HTML'` (`<b>`, `<a href>`)
- Receipt URL записывался в колонку U («Чеки») вместо T («ссылка на чек») из-за логики
  last-match-wins в `_find_columns_by_headers`. Исправлено: специфичный матч приоритетнее
- Ссылка на чек открывала скачивание вместо просмотра. Исправлено: `webViewLink` вместо `uc?export=download`
- Уведомление owner теперь откладывается до завершения загрузки чека (одно сообщение со ссылкой)

### 🗂️ Changed
- **Формат уведомлений по валютам:**
  - USDT (owner + инициатор): кошелёк, назначение, исполнитель, ID сделки
  - RUB/BYN/KZT (owner + инициатор): получатель, банк, назначение, исполнитель, ID сделки
- `.env` добавлен в `CORE_FILES` `vps_connect.py` — деплоится автоматически

---

## [2.5.0] - 2026-02-13

### 🔧 Fixed
- **CRITICAL:** Fixed encoding issue in `sheets.py::get_user()` function
  - Changed from using `get_all_records()` (which depends on header names) to `get_all_values()` with column indexes
  - This fixes the issue where users couldn't create requests because their roles weren't being read correctly
  - Affects: All users trying to create requests

### 📚 Added
- Comprehensive project audit (`PROJECT_AUDIT.md`)
- Reorganization plan (`REORGANIZATION_PLAN.md`)
- Skills and knowledge base documentation (`SKILLS_REQUIRED.md`)
- Automated reorganization script (`reorganize_project.py`)

### 🗂️ Changed
- Project structure preparation for best practices reorganization

---

## [2.4.4] - 2026-01-30

### ✨ Added
- CNY QR code upload with optional text requisites
- Ability to add both QR code AND text requisites for CNY payments

### 🔧 Fixed
- CNY QR code upload error handling
- Drive Manager initialization in bot_data

---

## [2.4.3] - 2026-01-29

### 🚀 Deployment
- Complete deployment automation with scripts
- Comprehensive deployment documentation
- VPS setup guide

### 📚 Documentation
- Added deployment scripts and guides
- Created comprehensive deploy report

---

## [2.4.2] - 2026-01-28

### ✨ Added
- CNY currency support with payment methods:
  - Alipay
  - WeChat Pay
  - Chinese bank card
- QR code handling for CNY payments via Google Drive
- Optional text requisites for CNY
- CNY view and edit support in bot interface

### 🗂️ Changed
- Updated sheets structure to include CNY sheet
- Added QR code link column (F) for CNY requests

### 📚 Documentation
- CNY setup script and testing guide
- Google Drive API configuration guide

---

## [2.4.0] - 2026-01-25

### ✨ Added
- CNY (Chinese Yuan) currency support
- Google Drive integration for QR code storage
- Drive Manager with OAuth2 authentication

### 🗂️ Changed
- Sheets structure updated for CNY
- Request handlers updated to support CNY flow

---

## [2.3.2] - 2026-01-20

### 🔧 Fixed
- Direct download links for receipt files
- Markdown special character escaping in receipt links

---

## [2.3.0] - 2026-01-18

### ✨ Added
- Receipt links in paid requests
- Back button fix in request navigation

### 🗂️ Changed
- Receipt display format
- Navigation flow improvements

---

## [2.2.0] - 2026-01-15

### ✨ Added
- KZT (Kazakhstan Tenge) currency support
- Card/phone number examples in prompts

### 🔧 Fixed
- "My Requests" command for all currencies
- `unsupported format string passed to NoneType` error

### 🗂️ Changed
- USDT structure unified with RUB/BYN (added author fields J, K, L)
- Requisites format changed to multiline (Card/Phone → Bank → Recipient)

---

## [2.1.0] - 2026-01-10

### ✨ Added
- Fact expense feature for ROLE_REPORT users
- New sheet: "Фактические расходы"
- Menu buttons role normalization
- Welcome message hints

### 🔧 Fixed
- Menu buttons for all roles
- Set_my_commands configuration

---

## [2.0.0] - 2026-01-05

### 🎉 Major Release

### ✨ Added
- Multi-currency support (RUB, BYN, USDT)
- Currency selection at request creation
- Status colors and emojis
- Direct payment flow (no approval step)
- Author information (ID, Username, Full Name)

### 🗂️ Changed
- New Google Sheets structure (14 columns)
- Removed approval workflow
- Simplified payment process

### 🔧 Fixed
- Critical blockers (missing imports, methods)
- Google API Manager dependencies
- AttributeError in append_row

---

## [1.5.0] - 2025-12-20

### ✨ Added
- USDT cryptocurrency support
- USDT sheet integration
- Wallet address validation

---

## [1.0.0] - 2025-12-01

### 🎉 Initial Release

### ✨ Features
- Request creation (RUB, BYN)
- Request approval workflow
- Payment execution
- Role-based access control (Owner, Manager, Executor)
- Google Sheets integration
- Telegram bot interface
- VPS deployment

---

## Legend

- 🎉 **Major Release** - Breaking changes or major new features
- ✨ **Added** - New features
- 🗂️ **Changed** - Changes in existing functionality
- 🔧 **Fixed** - Bug fixes
- 🚀 **Deployment** - Deployment-related changes
- 📚 **Documentation** - Documentation updates
- 🔒 **Security** - Security fixes
- ⚠️ **Deprecated** - Features marked for removal
- ❌ **Removed** - Removed features

---

## Versioning Guide

Format: `MAJOR.MINOR.PATCH`

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

---

## Upcoming Features

### Planned for 3.0.0
- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Prometheus metrics
- [ ] Health check endpoint
- [ ] Rate limiting
- [ ] Admin panel

### Planned for 2.6.0
- [ ] Request filters by date
- [ ] Export to Excel/PDF
- [ ] Request statistics dashboard
- [ ] Bulk operations

---

## Migration Guides

### From 2.4.x to 2.5.0
No breaking changes. Encoding fix is backwards compatible.

### From 2.3.x to 2.4.0
- Update Google Drive credentials (OAuth2)
- Add QR code column to CNY sheet
- Enable Google Drive API in Cloud Console

### From 2.0.x to 2.1.0
- Add "Фактические расходы" sheet
- Add ROLE_REPORT users to "Пользователи"

### From 1.x to 2.0.0
- Update Google Sheets structure (12 → 14 columns)
- Add author information columns (J, K, L)
- Remove approval workflow from code
- Update .env configuration

---

**For detailed information about specific versions, see:**
- `docs/reports/` - Release reports
- `docs/architecture/MIGRATION_GUIDE.md` - Migration guides
- `README.md` - Current version info
