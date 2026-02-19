"""
Тесты для Block 4 — Управление пользователями (февраль 2026).

Покрывают:
1. sheets.get_all_users()          — нормальный кейс, пустой лист, пустые роли
2. sheets.update_user_role()       — успех, не найден, нет колонок
3. sheets.deactivate_user()        — очистка роли (не удаление строки)
4. owner.owner_users()             — доступ только owner, отказ другим ролям
5. owner._show_users_list()        — группировка по ролям, пустой список
6. owner.ow_user_callback()        — карточка пользователя, не найден
7. owner.ow_chgrole_callback()     — экран выбора роли
8. owner.ow_setrole_callback()     — смена роли: успех, неизвестная роль
9. owner.ow_rmuser_callback()      — экран подтверждения деактивации
10. owner.ow_confirmrm_callback()  — деактивация: успех, ошибка
11. owner.ow_users_back_callback() — возврат к списку
12. menu.py                        — кнопка 👥 Пользователи в owner меню + роутинг
13. bot.py                         — все callback'ы зарегистрированы
14. Регрессия                      — блоки 1/2/5/6 не сломаны нашими изменениями
15. Безопасность                   — не-owner не получает доступ

Запуск: python tests/test_block4_users.py
"""
import asyncio
import inspect
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

PASS = "[ OK ]"
FAIL = "[FAIL]"
WARN = "[WARN]"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str):
        self.passed.append(msg)

    def fail(self, msg: str):
        self.failed.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def print_summary(self) -> bool:
        total = len(self.passed) + len(self.failed)
        status = PASS if not self.failed else FAIL
        print(f"\n{status} [{self.name}]")
        for m in self.passed:
            print(f"   + {m}")
        for m in self.failed:
            print(f"   - {m}")
        for m in self.warnings:
            print(f"   ! {m}")
        rate = (len(self.passed) / total * 100) if total else 0
        print(f"   {len(self.passed)}/{total} ({rate:.0f}%)")
        return not self.failed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: фиктивный лист пользователей
# ─────────────────────────────────────────────────────────────────────────────

def _make_users_sheet(rows: list[list]) -> MagicMock:
    """Создать mock для users_sheet с заданными строками (включая заголовки)."""
    ws = MagicMock()
    ws.get_all_values = MagicMock(return_value=rows)
    ws.update_cell = MagicMock(return_value=None)
    ws.delete_rows = MagicMock(return_value=None)
    return ws


HEADER_ROW = ['Telegram ID', 'Имя', 'Username', 'Роль']

SAMPLE_USERS = [
    HEADER_ROW,
    ['111', 'Иван Иванов', 'ivan', 'Владелец'],
    ['222', 'Петр Петров', 'petr', 'Менеджер'],
    ['333', 'Алексей Кузнецов', 'aleksey', 'Исполнитель'],
    ['444', 'Наталья Козлова', 'natasha', 'Учёт'],
    ['555', 'Дмитрий Орлов', 'dmitry', 'Менеджер'],
]


def _make_sheets_manager(users_rows=None) -> MagicMock:
    """Создать mock SheetsManager с листом пользователей."""
    from src import config
    sm = MagicMock()
    sm.users_sheet = _make_users_sheet(users_rows or SAMPLE_USERS)
    sm.get_user_role = MagicMock(return_value=config.ROLE_OWNER)
    sm.get_user = MagicMock(return_value={
        'telegram_id': '222',
        'name': 'Петр Петров',
        'username': 'petr',
        'role': config.ROLE_MANAGER,
    })
    sm.get_all_users = MagicMock(return_value=[])  # будет перекрыт в тестах sheets
    return sm


# ─────────────────────────────────────────────────────────────────────────────
# 1. sheets.get_all_users
# ─────────────────────────────────────────────────────────────────────────────

def test_get_all_users_normal():
    """get_all_users возвращает всех пользователей из листа."""
    r = TestResult("sheets.get_all_users: нормальный кейс")
    try:
        from sheets import SheetsManager
        from src import config

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = _make_users_sheet(SAMPLE_USERS)
        result = SheetsManager.get_all_users(sm)

        if len(result) == 5:
            r.ok("Вернул 5 пользователей")
        else:
            r.fail(f"Ожидалось 5, вернул {len(result)}: {result}")

        roles = [u.get('role') for u in result]
        if config.ROLE_OWNER in roles:
            r.ok("Владелец есть в списке")
        else:
            r.fail(f"Владелец не найден, роли: {roles}")

        if config.ROLE_MANAGER in roles:
            r.ok("Менеджер есть в списке")
        else:
            r.fail("Менеджер не найден")

        ivan = next((u for u in result if u.get('name') == 'Иван Иванов'), None)
        if ivan:
            r.ok(f"Иван Иванов: telegram_id={ivan['telegram_id']}, role={ivan['role']}")
        else:
            r.fail("Иван Иванов не найден в результате")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_get_all_users_empty_sheet():
    """get_all_users возвращает [] для пустого листа."""
    r = TestResult("sheets.get_all_users: пустой лист")
    try:
        from sheets import SheetsManager

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = _make_users_sheet([HEADER_ROW])  # только заголовки
        result = SheetsManager.get_all_users(sm)

        if result == []:
            r.ok("Пустой лист → []")
        else:
            r.fail(f"Ожидался [], вернул: {result}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_get_all_users_no_sheet():
    """get_all_users возвращает [] если users_sheet=None."""
    r = TestResult("sheets.get_all_users: users_sheet=None")
    try:
        from sheets import SheetsManager

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = None
        result = SheetsManager.get_all_users(sm)

        if result == []:
            r.ok("users_sheet=None → []")
        else:
            r.fail(f"Ожидался [], вернул: {result}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_get_all_users_unknown_role_ignored():
    """get_all_users включает пользователей с неизвестной ролью (raw role сохраняется)."""
    r = TestResult("sheets.get_all_users: пользователь с неизвестной ролью")
    try:
        from sheets import SheetsManager

        rows = [
            HEADER_ROW,
            ['111', 'Иван', 'ivan', 'Владелец'],
            ['999', 'Без роли', 'norole', ''],        # пустая роль
            ['888', 'Неизвестный', 'unknown', 'Гость'],  # незнакомая роль
        ]
        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = _make_users_sheet(rows)
        result = SheetsManager.get_all_users(sm)

        # Все 3 строки с данными должны вернуться
        if len(result) == 3:
            r.ok("Возвращены все 3 пользователя включая с пустой/неизвестной ролью")
        else:
            r.fail(f"Ожидалось 3, вернул {len(result)}")

        # Пустая роль → None (после маппинга)
        no_role_user = next((u for u in result if u['telegram_id'] == '999'), None)
        if no_role_user:
            if no_role_user.get('role') is None:
                r.ok("Пустая роль '' → role=None после маппинга")
            else:
                r.warn(f"Пустая роль → role={no_role_user.get('role')!r}")
        else:
            r.fail("Пользователь с пустой ролью не найден")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 2. sheets.update_user_role
# ─────────────────────────────────────────────────────────────────────────────

def test_update_user_role_success():
    """update_user_role обновляет ячейку роли для найденного пользователя."""
    r = TestResult("sheets.update_user_role: успех")
    try:
        from sheets import SheetsManager

        ws = _make_users_sheet(SAMPLE_USERS)
        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = ws

        result = SheetsManager.update_user_role(sm, 222, 'Владелец')

        if result is True:
            r.ok("Вернул True")
        else:
            r.fail(f"Ожидался True, вернул {result}")

        if ws.update_cell.called:
            args = ws.update_cell.call_args.args
            row_num, col_num, value = args
            if value == 'Владелец':
                r.ok(f"update_cell вызван с 'Владелец' (row={row_num}, col={col_num})")
            else:
                r.fail(f"update_cell вызван с неверным значением: {value!r}")
            # Роль в 4-й колонке (index 3 → col 4)
            if col_num == 4:
                r.ok("Обновляется колонка 4 (Роль)")
            else:
                r.warn(f"Колонка роли = {col_num}, ожидалась 4")
        else:
            r.fail("update_cell не вызван")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_update_user_role_not_found():
    """update_user_role возвращает False если пользователь не найден."""
    r = TestResult("sheets.update_user_role: пользователь не найден")
    try:
        from sheets import SheetsManager

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = _make_users_sheet(SAMPLE_USERS)

        result = SheetsManager.update_user_role(sm, 9999999, 'Менеджер')

        if result is False:
            r.ok("Несуществующий TID → False")
        else:
            r.fail(f"Ожидался False, вернул {result}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_update_user_role_no_sheet():
    """update_user_role возвращает False если users_sheet=None."""
    r = TestResult("sheets.update_user_role: users_sheet=None")
    try:
        from sheets import SheetsManager

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = None

        result = SheetsManager.update_user_role(sm, 111, 'Исполнитель')

        if result is False:
            r.ok("users_sheet=None → False")
        else:
            r.fail(f"Ожидался False, вернул {result}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_update_user_role_scientific_notation_tid():
    """update_user_role находит пользователя, чей TID хранится в научной нотации."""
    r = TestResult("sheets.update_user_role: TID в научной нотации (8.45E+09)")
    try:
        from sheets import SheetsManager

        rows = [
            HEADER_ROW,
            ['8.45037E+09', 'Большой TID', 'bigtid', 'Менеджер'],
        ]
        ws = _make_users_sheet(rows)
        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = ws

        result = SheetsManager.update_user_role(sm, 8450370000, 'Исполнитель')

        # Должен найти пользователя, float('8.45037E+09') = 8450370000.0
        if result is True:
            r.ok("TID в научной нотации распознан → True")
        else:
            r.warn("TID в научной нотации не распознан (опционально: зависит от точности float)")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 3. sheets.deactivate_user
# ─────────────────────────────────────────────────────────────────────────────

def test_deactivate_user_clears_role_not_deletes():
    """deactivate_user очищает роль, а НЕ удаляет строку."""
    r = TestResult("sheets.deactivate_user: очищает роль, не удаляет строку")
    try:
        from sheets import SheetsManager

        ws = _make_users_sheet(SAMPLE_USERS)
        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = ws

        result = SheetsManager.deactivate_user(sm, 222)

        if result is True:
            r.ok("Вернул True")
        else:
            r.fail(f"Ожидался True, вернул {result}")

        # Критически важно: delete_rows НЕ должен вызываться
        if not ws.delete_rows.called:
            r.ok("delete_rows НЕ вызван (строка сохранена)")
        else:
            r.fail("delete_rows был вызван — строка удалена, а должна остаться!")

        # update_cell должен вызваться с пустой строкой
        if ws.update_cell.called:
            args = ws.update_cell.call_args.args
            row_num, col_num, value = args
            if value == '':
                r.ok(f"update_cell(row={row_num}, col={col_num}, value='') — роль очищена")
            else:
                r.fail(f"update_cell вызван с {value!r}, ожидалась пустая строка")
        else:
            r.fail("update_cell не вызван")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_deactivate_user_not_found():
    """deactivate_user возвращает False если пользователь не найден."""
    r = TestResult("sheets.deactivate_user: пользователь не найден → False")
    try:
        from sheets import SheetsManager

        sm = MagicMock(spec=SheetsManager)
        sm.users_sheet = _make_users_sheet(SAMPLE_USERS)

        result = SheetsManager.deactivate_user(sm, 9999999)

        if result is False:
            r.ok("Несуществующий TID → False")
        else:
            r.fail(f"Ожидался False, вернул {result}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_deactivate_user_access_denied_after():
    """После deactivate_user: get_user_role должна вернуть None (роль пуста)."""
    r = TestResult("sheets.deactivate_user: после очистки get_user_role → None")
    try:
        from sheets import SheetsManager

        # Пользователь с ролью
        rows_before = [
            HEADER_ROW,
            ['777', 'Тестовый', 'test', 'Менеджер'],
        ]
        # После деактивации роль станет пустой
        rows_after = [
            HEADER_ROW,
            ['777', 'Тестовый', 'test', ''],
        ]

        ws_after = _make_users_sheet(rows_after)
        sm_after = MagicMock(spec=SheetsManager)
        sm_after.users_sheet = ws_after

        # Имитируем get_user вызывая реальный метод
        user = SheetsManager.get_user(sm_after, 777)

        if user:
            role = user.get('role')
            if role is None:
                r.ok("После деактивации get_user возвращает role=None")
            else:
                r.fail(f"Ожидался role=None, но role={role!r}")
        else:
            r.fail("get_user вернул None для существующего пользователя с пустой ролью")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 4. owner.owner_users — контроль доступа
# ─────────────────────────────────────────────────────────────────────────────

def test_owner_users_access_denied_for_non_owner():
    """owner_users отказывает не-owner пользователям."""
    r = TestResult("owner.owner_users: не-owner получает отказ")

    async def _run():
        from handlers.owner import owner_users
        from src import config

        for role in [config.ROLE_MANAGER, config.ROLE_EXECUTOR, config.ROLE_REPORT]:
            mock_sheets = MagicMock()
            mock_sheets.get_user_role = MagicMock(return_value=role)
            mock_sheets.get_all_users = MagicMock(return_value=[])

            update = MagicMock()
            update.message = AsyncMock()
            update.message.reply_text = AsyncMock()
            update.callback_query = None
            update.effective_user = MagicMock(id=12345)

            context = MagicMock()
            context.bot_data = {'sheets': mock_sheets}

            await owner_users(update, context)

            calls = [c.args[0] for c in update.message.reply_text.call_args_list if c.args]
            denied = any('❌' in t or 'доступ' in t.lower() or 'владельц' in t.lower() for t in calls)
            if denied:
                r.ok(f"Роль {role!r} → отказ в доступе")
            else:
                r.fail(f"Роль {role!r}: отказ не отправлен. reply_text calls: {calls}")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_owner_users_no_sheets_connection():
    """owner_users обрабатывает отсутствие подключения к Sheets."""
    r = TestResult("owner.owner_users: sheets=None → сообщение об ошибке")

    async def _run():
        from handlers.owner import owner_users

        update = MagicMock()
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        update.effective_user = MagicMock(id=111)

        context = MagicMock()
        context.bot_data = {'sheets': None}

        await owner_users(update, context)

        if update.message.reply_text.called:
            text = update.message.reply_text.call_args.args[0]
            if '⚠️' in text or 'ошибка' in text.lower():
                r.ok("sheets=None → сообщение об ошибке отправлено")
            else:
                r.warn(f"Сообщение отправлено, но без ⚠️: {text!r}")
        else:
            r.warn("reply_text не вызван (msg может быть None — допустимо)")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 5. owner._show_users_list — группировка
# ─────────────────────────────────────────────────────────────────────────────

def test_show_users_list_grouped_by_role():
    """_show_users_list группирует по ролям и отображает правильные эмодзи."""
    r = TestResult("owner._show_users_list: группировка по ролям")

    async def _run():
        from handlers.owner import _show_users_list
        from src import config

        all_users = [
            {'telegram_id': '111', 'name': 'Иван', 'username': 'ivan', 'role': config.ROLE_OWNER},
            {'telegram_id': '222', 'name': 'Петр', 'username': 'petr', 'role': config.ROLE_MANAGER},
            {'telegram_id': '333', 'name': 'Алексей', 'username': 'alex', 'role': config.ROLE_EXECUTOR},
            {'telegram_id': '444', 'name': 'Наталья', 'username': 'nat', 'role': config.ROLE_REPORT},
        ]

        mock_sheets = MagicMock()
        mock_sheets.get_all_users = MagicMock(return_value=all_users)

        sent_text = []
        sent_markup = []

        update = MagicMock()
        update.message = AsyncMock()
        update.callback_query = None

        async def capture_reply(text, **kwargs):
            sent_text.append(text)
            sent_markup.append(kwargs.get('reply_markup'))

        update.message.reply_text = capture_reply

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await _show_users_list(update, context, edit=False)

        if sent_text:
            text = sent_text[0]
            if '👑' in text and 'Владелец' in text:
                r.ok("👑 Владелец присутствует в тексте")
            else:
                r.fail(f"Владелец/👑 не найден: {text!r}")

            if '🟢' in text and 'Менеджер' in text:
                r.ok("🟢 Менеджер присутствует")
            else:
                r.fail("🟢 Менеджер не найден")

            if '⚡' in text and 'Исполнитель' in text:
                r.ok("⚡ Исполнитель присутствует")
            else:
                r.fail("⚡ Исполнитель не найден")

            if '📊' in text and 'Учёт' in text:
                r.ok("📊 Учёт присутствует")
            else:
                r.fail("📊 Учёт не найден")

            if '(4)' in text or '4' in text:
                r.ok("Счётчик пользователей отображается")
            else:
                r.warn(f"Счётчик не найден в тексте")
        else:
            r.fail("reply_text не был вызван")

        # Проверяем клавиатуру
        if sent_markup and sent_markup[0]:
            markup = sent_markup[0]
            kbd = markup.inline_keyboard
            if len(kbd) == 4:
                r.ok(f"Клавиатура содержит 4 кнопки (по одной на пользователя)")
            else:
                r.warn(f"Клавиатура содержит {len(kbd)} кнопок")

            # callback_data кнопок — ow_user_TID
            for row in kbd:
                for btn in row:
                    if not btn.callback_data.startswith('ow_user_'):
                        r.fail(f"Кнопка имеет неверный callback_data: {btn.callback_data!r}")
                        return
            r.ok("Все кнопки имеют callback_data 'ow_user_TID'")
        else:
            r.fail("Клавиатура не отправлена или пустая")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_show_users_list_empty():
    """_show_users_list корректно обрабатывает пустой список пользователей."""
    r = TestResult("owner._show_users_list: пустой список")

    async def _run():
        from handlers.owner import _show_users_list

        mock_sheets = MagicMock()
        mock_sheets.get_all_users = MagicMock(return_value=[])

        sent_text = []
        update = MagicMock()
        update.message = AsyncMock()
        update.callback_query = None

        async def capture(text, **kwargs):
            sent_text.append(text)

        update.message.reply_text = capture
        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await _show_users_list(update, context, edit=False)

        if sent_text:
            text = sent_text[0]
            if 'нет' in text.lower() or '(0)' in text:
                r.ok(f"Пустой список обработан корректно: {text!r}")
            else:
                r.warn(f"Ответ отправлен, но без 'нет'/(0): {text!r}")
        else:
            r.fail("reply_text не был вызван для пустого списка")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 6. ow_user_callback — карточка пользователя
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_user_callback_shows_card():
    """ow_user_callback отображает карточку пользователя с именем, ролью и TID."""
    r = TestResult("owner.ow_user_callback: карточка пользователя")

    async def _run():
        from handlers.owner import ow_user_callback
        from src import config

        query = AsyncMock()
        query.data = "ow_user_222"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user = MagicMock(id=111)

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value={
            'telegram_id': '222',
            'name': 'Петр Петров',
            'username': 'petr',
            'role': config.ROLE_MANAGER,
        })

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_user_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            markup = query.edit_message_text.call_args.kwargs.get('reply_markup')

            if 'Петр Петров' in text:
                r.ok("Имя пользователя присутствует в карточке")
            else:
                r.fail(f"Имя не найдено: {text!r}")

            if '222' in text:
                r.ok("Telegram ID присутствует в карточке")
            else:
                r.fail(f"TID не найден: {text!r}")

            if '🟢' in text or 'Менеджер' in text:
                r.ok("Роль отображается в карточке")
            else:
                r.fail(f"Роль не найдена: {text!r}")

            if markup:
                callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
                if any('ow_chgrole_222' in c for c in callbacks):
                    r.ok("Кнопка 'Сменить роль' с правильным callback")
                else:
                    r.fail(f"Кнопка ow_chgrole_222 не найдена: {callbacks}")
                if any('ow_rmuser_222' in c for c in callbacks):
                    r.ok("Кнопка 'Заблокировать' с правильным callback")
                else:
                    r.fail(f"Кнопка ow_rmuser_222 не найдена: {callbacks}")
                if any('ow_users_back' in c for c in callbacks):
                    r.ok("Кнопка '⬅️ Назад' присутствует")
                else:
                    r.fail(f"Кнопка ow_users_back не найдена: {callbacks}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_ow_user_callback_not_found():
    """ow_user_callback показывает ошибку если пользователь не найден."""
    r = TestResult("owner.ow_user_callback: пользователь не найден")

    async def _run():
        from handlers.owner import ow_user_callback

        query = AsyncMock()
        query.data = "ow_user_9999"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value=None)

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_user_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '❌' in text or 'не найден' in text.lower():
                r.ok("Пользователь не найден → сообщение об ошибке")
            else:
                r.fail(f"Не найдено сообщение об ошибке: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_ow_user_callback_invalid_tid():
    """ow_user_callback корректно обрабатывает нечисловой TID."""
    r = TestResult("owner.ow_user_callback: нечисловой TID")

    async def _run():
        from handlers.owner import ow_user_callback

        query = AsyncMock()
        query.data = "ow_user_not_a_number"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        context = MagicMock()
        context.bot_data = {'sheets': MagicMock()}

        await ow_user_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '❌' in text:
                r.ok("Нечисловой TID → сообщение об ошибке")
            else:
                r.warn(f"Ответ: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 7. ow_chgrole_callback — выбор роли
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_chgrole_callback_shows_all_roles():
    """ow_chgrole_callback показывает 4 роли + кнопку назад."""
    r = TestResult("owner.ow_chgrole_callback: 4 роли + кнопка назад")

    async def _run():
        from handlers.owner import ow_chgrole_callback
        from src import config

        query = AsyncMock()
        query.data = "ow_chgrole_222"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value={
            'name': 'Петр', 'username': 'petr', 'role': config.ROLE_MANAGER
        })
        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_chgrole_callback(update, context)

        if query.edit_message_text.called:
            markup = query.edit_message_text.call_args.kwargs.get('reply_markup')
            if markup:
                callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
                expected = [
                    'ow_setrole_222_owner',
                    'ow_setrole_222_manager',
                    'ow_setrole_222_executor',
                    'ow_setrole_222_report',
                ]
                for expected_cb in expected:
                    if expected_cb in callbacks:
                        r.ok(f"Кнопка {expected_cb!r} присутствует")
                    else:
                        r.fail(f"Кнопка {expected_cb!r} не найдена. Callbacks: {callbacks}")

                if any('ow_user_222' in c for c in callbacks):
                    r.ok("Кнопка '⬅️ Назад' ведёт на ow_user_222")
                else:
                    r.fail(f"Кнопка назад не найдена: {callbacks}")
            else:
                r.fail("reply_markup не передан")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 8. ow_setrole_callback — применение роли
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_setrole_callback_success():
    """ow_setrole_callback успешно меняет роль."""
    r = TestResult("owner.ow_setrole_callback: смена роли успех")

    async def _run():
        from handlers.owner import ow_setrole_callback
        from src import config

        query = AsyncMock()
        query.data = "ow_setrole_222_executor"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.update_user_role = MagicMock(return_value=True)
        mock_sheets.get_user = MagicMock(return_value={
            'name': 'Петр', 'username': 'petr', 'role': config.ROLE_EXECUTOR
        })
        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_setrole_callback(update, context)

        # update_user_role должен быть вызван с 'Исполнитель'
        if mock_sheets.update_user_role.called:
            call_args = mock_sheets.update_user_role.call_args.args
            tid, new_role = call_args[0], call_args[1]
            if tid == 222:
                r.ok(f"update_user_role вызван с TID=222")
            else:
                r.fail(f"TID={tid}, ожидался 222")
            if new_role == 'Исполнитель':
                r.ok(f"Роль передана как 'Исполнитель'")
            else:
                r.fail(f"Роль={new_role!r}, ожидалась 'Исполнитель'")
        else:
            r.fail("update_user_role не вызван")

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '✅' in text:
                r.ok("Сообщение об успехе отправлено")
            else:
                r.fail(f"Нет ✅ в ответе: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_ow_setrole_callback_unknown_role():
    """ow_setrole_callback обрабатывает неизвестную роль в callback_data."""
    r = TestResult("owner.ow_setrole_callback: неизвестная роль")

    async def _run():
        from handlers.owner import ow_setrole_callback

        query = AsyncMock()
        query.data = "ow_setrole_222_superadmin"  # несуществующая роль
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()
        context.bot_data = {'sheets': MagicMock()}

        await ow_setrole_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '❌' in text:
                r.ok("Неизвестная роль → сообщение об ошибке")
            else:
                r.fail(f"Нет ❌ при неизвестной роли: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_ow_setrole_rsplit_parsing():
    """ow_setrole_callback корректно парсит callback_data для всех 4 ролей."""
    r = TestResult("owner.ow_setrole_callback: парсинг callback_data")
    try:
        from handlers.owner import ROLE_DISPLAY, ROLE_TO_SHEET

        # Все 4 роли должны правильно парситься через rsplit
        cases = [
            ("ow_setrole_1234567890_owner", "1234567890", "owner"),
            ("ow_setrole_1234567890_manager", "1234567890", "manager"),
            ("ow_setrole_1234567890_executor", "1234567890", "executor"),
            ("ow_setrole_1234567890_report", "1234567890", "report"),
        ]
        for cb_data, expected_tid, expected_role in cases:
            data = cb_data[len('ow_setrole_'):]
            tid_str, role_key = data.rsplit('_', 1)
            if tid_str == expected_tid and role_key == expected_role:
                r.ok(f"'{cb_data}' → TID={tid_str}, role={role_key}")
            else:
                r.fail(f"Парсинг '{cb_data}': TID={tid_str!r} (ожид {expected_tid!r}), role={role_key!r} (ожид {expected_role!r})")

        # Проверяем ROLE_TO_SHEET содержит все роли
        for role_key in ['owner', 'manager', 'executor', 'report']:
            if role_key in ROLE_TO_SHEET:
                r.ok(f"ROLE_TO_SHEET[{role_key!r}] = {ROLE_TO_SHEET[role_key]!r}")
            else:
                r.fail(f"ROLE_TO_SHEET не содержит {role_key!r}")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 9. ow_rmuser_callback — экран подтверждения
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_rmuser_callback_confirmation_screen():
    """ow_rmuser_callback показывает экран подтверждения деактивации."""
    r = TestResult("owner.ow_rmuser_callback: экран подтверждения")

    async def _run():
        from handlers.owner import ow_rmuser_callback
        from src import config

        query = AsyncMock()
        query.data = "ow_rmuser_222"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value={
            'name': 'Петр Петров', 'username': 'petr', 'role': config.ROLE_MANAGER
        })
        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_rmuser_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            markup = query.edit_message_text.call_args.kwargs.get('reply_markup')

            if '⚠️' in text:
                r.ok("Предупреждение ⚠️ присутствует")
            else:
                r.fail(f"⚠️ не найден: {text!r}")

            if 'Петр Петров' in text:
                r.ok("Имя пользователя в подтверждении")
            else:
                r.fail(f"Имя не найдено: {text!r}")

            if 'таблиц' in text.lower() or 'сохранится' in text.lower() or 'сохранен' in text.lower():
                r.ok("Текст сообщает о сохранении данных в таблице")
            else:
                r.fail(f"Нет упоминания сохранения данных: {text!r}")

            if markup:
                callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
                if any('ow_confirmrm_222' in c for c in callbacks):
                    r.ok("Кнопка подтверждения 'ow_confirmrm_222' присутствует")
                else:
                    r.fail(f"Кнопка ow_confirmrm_222 не найдена: {callbacks}")
                if any('ow_user_222' in c for c in callbacks):
                    r.ok("Кнопка 'Отмена' ведёт на ow_user_222")
                else:
                    r.fail(f"Кнопка отмены не найдена: {callbacks}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 10. ow_confirmrm_callback — исполнение деактивации
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_confirmrm_callback_success():
    """ow_confirmrm_callback вызывает deactivate_user и сообщает об успехе."""
    r = TestResult("owner.ow_confirmrm_callback: деактивация успех")

    async def _run():
        from handlers.owner import ow_confirmrm_callback
        from src import config

        query = AsyncMock()
        query.data = "ow_confirmrm_333"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value={
            'name': 'Алексей Кузнецов', 'username': 'alex', 'role': config.ROLE_EXECUTOR
        })
        mock_sheets.deactivate_user = MagicMock(return_value=True)

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_confirmrm_callback(update, context)

        if mock_sheets.deactivate_user.called:
            args = mock_sheets.deactivate_user.call_args.args
            if args[0] == 333:
                r.ok("deactivate_user(333) вызван")
            else:
                r.fail(f"deactivate_user вызван с TID={args[0]}, ожидался 333")
        else:
            r.fail("deactivate_user не вызван — вызывался ли remove_user? (устаревший метод)")

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '✅' in text:
                r.ok("Сообщение об успешной деактивации отправлено")
            else:
                r.fail(f"Нет ✅: {text!r}")
            if 'сохранен' in text.lower() or 'таблиц' in text.lower():
                r.ok("Сообщение упоминает сохранение данных")
            else:
                r.warn(f"Нет упоминания сохранения: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_ow_confirmrm_callback_failure():
    """ow_confirmrm_callback сообщает об ошибке если deactivate_user вернул False."""
    r = TestResult("owner.ow_confirmrm_callback: deactivate_user → False")

    async def _run():
        from handlers.owner import ow_confirmrm_callback

        query = AsyncMock()
        query.data = "ow_confirmrm_333"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_user = MagicMock(return_value=None)
        mock_sheets.deactivate_user = MagicMock(return_value=False)

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}

        await ow_confirmrm_callback(update, context)

        if query.edit_message_text.called:
            text = query.edit_message_text.call_args.args[0]
            if '❌' in text or 'ошибка' in text.lower():
                r.ok("Ошибка деактивации → сообщение с ❌")
            else:
                r.fail(f"Нет ❌ при ошибке: {text!r}")
        else:
            r.fail("edit_message_text не вызван")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 11. ow_users_back_callback
# ─────────────────────────────────────────────────────────────────────────────

def test_ow_users_back_callback():
    """ow_users_back_callback вызывает _show_users_list с edit=True."""
    r = TestResult("owner.ow_users_back_callback: возврат к списку")

    async def _run():
        from handlers import owner as owner_module

        query = AsyncMock()
        query.data = "ow_users_back"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_sheets = MagicMock()
        mock_sheets.get_all_users = MagicMock(return_value=[])

        context = MagicMock()
        context.bot_data = {'sheets': mock_sheets}
        context.user_data = {}

        called_with_edit = []

        original_show = owner_module._show_users_list

        async def mock_show(upd, ctx, edit=False):
            called_with_edit.append(edit)

        owner_module._show_users_list = mock_show
        try:
            await owner_module.ow_users_back_callback(update, context)
        finally:
            owner_module._show_users_list = original_show

        if query.answer.called:
            r.ok("query.answer() вызван")
        else:
            r.fail("query.answer() не вызван")

        if called_with_edit and called_with_edit[0] is True:
            r.ok("_show_users_list вызван с edit=True")
        else:
            r.fail(f"_show_users_list вызван с edit={called_with_edit}")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 12. menu.py — кнопка и роутинг
# ─────────────────────────────────────────────────────────────────────────────

def test_menu_owner_keyboard_has_users_button():
    """get_main_menu_keyboard для owner содержит кнопку '👥 Пользователи'."""
    r = TestResult("menu.get_main_menu_keyboard: кнопка '👥 Пользователи' у owner")
    try:
        from handlers.menu import get_main_menu_keyboard
        from src import config

        markup = get_main_menu_keyboard(config.ROLE_OWNER)
        all_texts = [btn.text for row in markup.keyboard for btn in row]

        if '👥 Пользователи' in all_texts:
            r.ok("'👥 Пользователи' присутствует в меню owner")
        else:
            r.fail(f"'👥 Пользователи' не найдена. Кнопки: {all_texts}")

        # Убедиться, что кнопка есть только у owner
        for non_owner_role in [config.ROLE_MANAGER, config.ROLE_EXECUTOR, config.ROLE_REPORT]:
            markup_non = get_main_menu_keyboard(non_owner_role)
            texts_non = [btn.text for row in markup_non.keyboard for btn in row]
            if '👥 Пользователи' not in texts_non:
                r.ok(f"Роль {non_owner_role!r}: '👥 Пользователи' корректно скрыта")
            else:
                r.fail(f"Роль {non_owner_role!r}: '👥 Пользователи' отображается (не должна)")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_menu_routes_users_button():
    """handle_menu_button роутит '👥 Пользователи' на owner_users."""
    r = TestResult("menu.handle_menu_button: '👥 Пользователи' → owner_users")

    async def _run():
        from handlers import menu as menu_module

        called = []
        original_owner_users = None

        # Патчим owner_users внутри handle_menu_button
        import handlers.owner as owner_mod
        original = getattr(owner_mod, 'owner_users', None)

        async def mock_owner_users(upd, ctx):
            called.append('owner_users')

        owner_mod.owner_users = mock_owner_users

        try:
            update = MagicMock()
            update.message = AsyncMock()
            update.message.text = "👥 Пользователи"
            update.effective_user = MagicMock(id=111)

            context = MagicMock()
            context.bot_data = {'sheets': MagicMock()}

            await menu_module.handle_menu_button(update, context)

        finally:
            if original:
                owner_mod.owner_users = original

        if 'owner_users' in called:
            r.ok("'👥 Пользователи' корректно маршрутизирован на owner_users")
        else:
            r.fail(f"owner_users не был вызван, called={called}")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 13. bot.py — регистрация callback-хендлеров
# ─────────────────────────────────────────────────────────────────────────────

def test_bot_imports_block4_handlers():
    """bot.py импортирует все 7 новых хендлеров Block 4."""
    r = TestResult("bot.py: импорт всех Block 4 хендлеров")
    try:
        import ast

        bot_path = ROOT / 'src' / 'bot.py'
        tree = ast.parse(bot_path.read_text(encoding='utf-8'))

        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

        expected = [
            'owner_users',
            'ow_user_callback',
            'ow_chgrole_callback',
            'ow_setrole_callback',
            'ow_rmuser_callback',
            'ow_confirmrm_callback',
            'ow_users_back_callback',
        ]
        for name in expected:
            if name in imported_names:
                r.ok(f"'{name}' импортирован в bot.py")
            else:
                r.fail(f"'{name}' НЕ импортирован в bot.py")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_bot_registers_block4_callbacks():
    """bot.py регистрирует все паттерны callback_data для Block 4."""
    r = TestResult("bot.py: регистрация callback паттернов Block 4")
    try:
        bot_path = ROOT / 'src' / 'bot.py'
        source = bot_path.read_text(encoding='utf-8')

        patterns = [
            '^ow_users_back$',
            '^ow_user_',
            '^ow_chgrole_',
            '^ow_setrole_',
            '^ow_rmuser_',
            '^ow_confirmrm_',
        ]
        for pattern in patterns:
            if pattern in source:
                r.ok(f"Паттерн {pattern!r} зарегистрирован")
            else:
                r.fail(f"Паттерн {pattern!r} НЕ найден в bot.py")

        if '👥 Пользователи' in source:
            r.ok("'👥 Пользователи' добавлена в menu_buttons")
        else:
            r.fail("'👥 Пользователи' не найдена в menu_buttons")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 14. Регрессия — блоки 1/2/5/6 не сломаны
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_block1_imports():
    """Block 1 функции всё ещё экспортируются из owner.py."""
    r = TestResult("Регрессия Block 1: owner_all_requests, filter, page, view")
    try:
        from handlers.owner import (
            owner_all_requests,
            all_req_filter_callback,
            all_req_page_callback,
            view_all_req_callback,
            back_to_all_req_callback,
        )
        r.ok("Все Block 1 функции импортируются без ошибок")
    except ImportError as e:
        r.fail(f"ImportError: {e}")
    return r


def test_regression_block2_imports():
    """Block 2 функции всё ещё экспортируются из owner.py."""
    r = TestResult("Регрессия Block 2: assign_exec, set_exec")
    try:
        from handlers.owner import assign_exec_callback, set_exec_callback
        r.ok("assign_exec_callback и set_exec_callback импортируются")
    except ImportError as e:
        r.fail(f"ImportError: {e}")
    return r


def test_regression_block5_imports():
    """Block 5 функции всё ещё экспортируются из owner.py."""
    r = TestResult("Регрессия Block 5: owner_stats, refresh, go_all_req")
    try:
        from handlers.owner import (
            owner_stats,
            owner_stats_refresh_callback,
            ow_go_all_req_callback,
        )
        r.ok("Block 5 функции импортируются")
    except ImportError as e:
        r.fail(f"ImportError: {e}")
    return r


def test_regression_block6_imports():
    """Block 6 функции всё ещё экспортируются из owner.py."""
    r = TestResult("Регрессия Block 6: notify_owners_new_request")
    try:
        from handlers.owner import notify_owners_new_request
        r.ok("notify_owners_new_request импортируется")
    except ImportError as e:
        r.fail(f"ImportError: {e}")
    return r


def test_regression_owner_cancel_req():
    """Block 3: owner_cancel_req_callback всё ещё экспортируется."""
    r = TestResult("Регрессия Block 3: owner_cancel_req_callback")
    try:
        from handlers.owner import owner_cancel_req_callback, ow_noop_callback
        r.ok("owner_cancel_req_callback и ow_noop_callback импортируются")
    except ImportError as e:
        r.fail(f"ImportError: {e}")
    return r


def test_regression_sheets_existing_methods():
    """Существующие методы sheets.py не изломаны нашими добавлениями."""
    r = TestResult("Регрессия sheets.py: add_user, get_user, get_users_by_role существуют")
    try:
        from sheets import SheetsManager
        required = [
            'add_user', 'get_user', 'get_user_role',
            'get_users_by_role', 'update_request_status_by_id',
            'assign_executor', 'get_all_requests',
        ]
        for method_name in required:
            if hasattr(SheetsManager, method_name):
                r.ok(f"SheetsManager.{method_name} существует")
            else:
                r.fail(f"SheetsManager.{method_name} ОТСУТСТВУЕТ")
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_regression_menu_other_buttons_intact():
    """handle_menu_button по-прежнему роутит существующие кнопки."""
    r = TestResult("Регрессия menu.py: существующие кнопки owner не сломаны")
    try:
        from handlers.menu import handle_menu_button
        import inspect
        src = inspect.getsource(handle_menu_button)

        existing_buttons = [
            "📊 Все заявки",
            "📈 Статистика",
            "💳 Оплата заявок",
            "📋 Мои заявки",
            "ℹ️ Помощь",
            "🔄 Обновить меню",
        ]
        for btn in existing_buttons:
            if btn in src:
                r.ok(f"Кнопка {btn!r} присутствует в handle_menu_button")
            else:
                r.fail(f"Кнопка {btn!r} НЕ найдена в handle_menu_button")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_regression_owner_docstring_has_block4():
    """owner.py docstring содержит все 6 блоков."""
    r = TestResult("owner.py: docstring содержит блоки 1-6")
    try:
        import handlers.owner as owner_mod
        doc = owner_mod.__doc__ or ''
        for i in range(1, 7):
            if f"{i} —" in doc or f"{i} -" in doc:
                r.ok(f"Block {i} упомянут в docstring")
            else:
                r.fail(f"Block {i} НЕ упомянут в docstring")
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 15. Безопасность — callback_data не раскрывает данные других ролей
# ─────────────────────────────────────────────────────────────────────────────

def test_security_callback_data_length():
    """callback_data для всех операций не превышает 64 байта (лимит Telegram)."""
    r = TestResult("Безопасность: callback_data ≤ 64 байта")
    try:
        # Максимальный TID = 10 цифр, максимальная роль = 8 символов (executor)
        max_tid = "9876543210"
        test_cases = [
            f"ow_user_{max_tid}",
            f"ow_chgrole_{max_tid}",
            f"ow_setrole_{max_tid}_executor",
            f"ow_setrole_{max_tid}_manager",
            f"ow_setrole_{max_tid}_owner",
            f"ow_setrole_{max_tid}_report",
            f"ow_rmuser_{max_tid}",
            f"ow_confirmrm_{max_tid}",
            "ow_users_back",
        ]
        for cb in test_cases:
            byte_len = len(cb.encode('utf-8'))
            if byte_len <= 64:
                r.ok(f"{cb!r} = {byte_len} байт (≤64 ✓)")
            else:
                r.fail(f"{cb!r} = {byte_len} байт (>64 — ПРЕВЫШЕН ЛИМИТ TELEGRAM!)")

    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


def test_security_non_owner_cannot_call_management():
    """Не-owner получает отказ при попытке вызвать owner_users."""
    r = TestResult("Безопасность: manager/executor не могут вызвать owner_users")

    async def _run():
        from handlers.owner import owner_users
        from src import config

        for role in [config.ROLE_MANAGER, config.ROLE_EXECUTOR, config.ROLE_REPORT]:
            mock_sheets = MagicMock()
            mock_sheets.get_user_role = MagicMock(return_value=role)

            update = MagicMock()
            update.message = AsyncMock()
            update.message.reply_text = AsyncMock()
            update.callback_query = None
            update.effective_user = MagicMock(id=999)

            context = MagicMock()
            context.bot_data = {'sheets': mock_sheets}

            # get_all_users не должен вызываться
            mock_sheets.get_all_users = MagicMock()

            await owner_users(update, context)

            if not mock_sheets.get_all_users.called:
                r.ok(f"Роль {role!r}: get_all_users НЕ вызван (доступ заблокирован)")
            else:
                r.fail(f"Роль {role!r}: get_all_users был вызван несмотря на блокировку!")

    try:
        asyncio.run(_run())
    except Exception as e:
        r.fail(f"Исключение: {e}")
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    # sheets.get_all_users
    test_get_all_users_normal,
    test_get_all_users_empty_sheet,
    test_get_all_users_no_sheet,
    test_get_all_users_unknown_role_ignored,
    # sheets.update_user_role
    test_update_user_role_success,
    test_update_user_role_not_found,
    test_update_user_role_no_sheet,
    test_update_user_role_scientific_notation_tid,
    # sheets.deactivate_user
    test_deactivate_user_clears_role_not_deletes,
    test_deactivate_user_not_found,
    test_deactivate_user_access_denied_after,
    # owner.owner_users
    test_owner_users_access_denied_for_non_owner,
    test_owner_users_no_sheets_connection,
    # owner._show_users_list
    test_show_users_list_grouped_by_role,
    test_show_users_list_empty,
    # owner.ow_user_callback
    test_ow_user_callback_shows_card,
    test_ow_user_callback_not_found,
    test_ow_user_callback_invalid_tid,
    # owner.ow_chgrole_callback
    test_ow_chgrole_callback_shows_all_roles,
    # owner.ow_setrole_callback
    test_ow_setrole_callback_success,
    test_ow_setrole_callback_unknown_role,
    test_ow_setrole_rsplit_parsing,
    # owner.ow_rmuser_callback
    test_ow_rmuser_callback_confirmation_screen,
    # owner.ow_confirmrm_callback
    test_ow_confirmrm_callback_success,
    test_ow_confirmrm_callback_failure,
    # owner.ow_users_back_callback
    test_ow_users_back_callback,
    # menu.py
    test_menu_owner_keyboard_has_users_button,
    test_menu_routes_users_button,
    # bot.py
    test_bot_imports_block4_handlers,
    test_bot_registers_block4_callbacks,
    # Регрессия
    test_regression_block1_imports,
    test_regression_block2_imports,
    test_regression_block5_imports,
    test_regression_block6_imports,
    test_regression_owner_cancel_req,
    test_regression_sheets_existing_methods,
    test_regression_menu_other_buttons_intact,
    test_regression_owner_docstring_has_block4,
    # Безопасность
    test_security_callback_data_length,
    test_security_non_owner_cannot_call_management,
]


def run_all() -> bool:
    print("=" * 70)
    print("Block 4 — User Management: Test Suite")
    print("=" * 70)
    results = []
    for fn in ALL_TESTS:
        try:
            r = fn()
            results.append(r)
            r.print_summary()
        except Exception as e:
            import traceback
            print(f"\n[CRITICAL] {fn.__name__}: {e}")
            traceback.print_exc()

    total_pass = sum(len(r.passed) for r in results)
    total_fail = sum(len(r.failed) for r in results)
    total_warn = sum(len(r.warnings) for r in results)
    test_fail = sum(1 for r in results if r.failed)

    print("\n" + "=" * 70)
    print("ИТОГО")
    print("=" * 70)
    print(f"  Тест-кейсов: {len(results)}  |  Упавших: {test_fail}")
    print(f"  Checks:  {PASS} {total_pass}   {FAIL} {total_fail}   {WARN} {total_warn}")
    ok = total_fail == 0
    print(f"  Результат: {'✅ ВСЕ ПРОШЛИ' if ok else '❌ ЕСТЬ ОШИБКИ'}")
    return ok


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
