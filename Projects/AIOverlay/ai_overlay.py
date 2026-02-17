"""
AI Overlay для AyuGram
С автообучением стилю и несколькими вариантами ответов
"""
import sys
import time
import ctypes
import json
import pyperclip
import keyboard
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime

# Включаем четкий рендеринг на Windows (DPI awareness)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# Файлы
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.txt"

# Claude API - читаем из config.txt
CLAUDE_API_KEY = ""
CLAUDE_MODEL = "claude-sonnet-4-5"

try:
    config_text = CONFIG_FILE.read_text(encoding='utf-8')
    import re
    key_match = re.search(r'API_KEY:\s*(.+)', config_text)
    model_match = re.search(r'MODEL:\s*(.+)', config_text)
    if key_match:
        CLAUDE_API_KEY = key_match.group(1).strip()
    if model_match:
        CLAUDE_MODEL = model_match.group(1).strip()
except:
    pass

if not CLAUDE_API_KEY:
    print("[!] API key not found in config.txt")
    print("    Create config.txt with: API_KEY: your-key-here")
INSTRUCTIONS_FILE = BASE_DIR / "custom_instructions.txt"
HISTORY_FILE = BASE_DIR / "style_history.json"
LEARNED_STYLE_FILE = BASE_DIR / "learned_style.txt"

# Загружаем правила стиля и имена пользователя
MY_NAMES = []
try:
    raw_instructions = INSTRUCTIONS_FILE.read_text(encoding='utf-8')
    # Парсим имена пользователя (несколько через запятую)
    import re
    names_match = re.search(r'MY_NAMES?:\s*(.+)', raw_instructions)
    if names_match:
        MY_NAMES = [n.strip() for n in names_match.group(1).split(',') if n.strip()]
    CUSTOM_INSTRUCTIONS = raw_instructions
except:
    CUSTOM_INSTRUCTIONS = """
- НЕ использовать длинное тире (—), только дефис (-)
- НЕ использовать двоеточие (:) без необходимости
- Писать естественно, как в обычной переписке
- Быть кратким и по делу
- Адаптироваться под стиль собеседника
""".strip()

# Загружаем выученный стиль
try:
    LEARNED_STYLE = LEARNED_STYLE_FILE.read_text(encoding='utf-8')
except:
    LEARNED_STYLE = ""

def load_history():
    """Загружает историю ответов"""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
    except:
        pass
    return []

def save_to_history(context, chosen_reply, reply_type):
    """Сохраняет выбранный ответ в историю для обучения"""
    history = load_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "context_preview": context[-200:],  # Последние 200 символов контекста
        "reply": chosen_reply,
        "type": reply_type  # short/medium/long
    })
    # Храним последние 50 записей
    history = history[-50:]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

    # Каждые 10 ответов - анализируем стиль
    if len(history) % 10 == 0:
        analyze_style(history)

def analyze_style(history):
    """Анализирует историю и обновляет выученный стиль"""
    if len(history) < 5:
        return

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, timeout=60.0)

        # Собираем примеры ответов
        examples = "\n---\n".join([h["reply"] for h in history[-15:]])

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Проанализируй эти примеры ответов пользователя и выдели ключевые особенности его стиля письма:

{examples}

Напиши краткий список правил (5-10 пунктов) которые описывают стиль этого человека:
- длина предложений
- использование эмодзи
- формальность/неформальность
- характерные слова и обороты
- пунктуация
- другие паттерны

Формат: простой список с дефисами, без заголовков."""
            }]
        )

        learned = response.content[0].text
        LEARNED_STYLE_FILE.write_text(learned, encoding='utf-8')
        print(f"[STYLE] Updated learned style")

    except Exception as e:
        print(f"[STYLE ERROR] {e}")

print("="*60)
print("  AI Overlay")
print("="*60)
if MY_NAMES:
    print(f"  User: {', '.join(MY_NAMES)}")
print("-"*60)
print("  F9  = Ответ на скопированный текст (Ctrl+C -> F9)")
print("  F8  = Свободный ввод (без контекста)")
print("="*60 + "\n")

def get_clipboard():
    """Читает буфер обмена"""
    try:
        text = pyperclip.paste()
        if text and text.strip():
            return text
        return None
    except:
        return None

def get_ai_replies(chat_text, custom_prompt=""):
    """Получает 3 варианта ответа от Claude AI"""
    try:
        import anthropic

        # Перезагружаем выученный стиль
        try:
            learned = LEARNED_STYLE_FILE.read_text(encoding='utf-8')
        except:
            learned = ""

        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, timeout=90.0)

        style_section = ""
        if learned:
            style_section = f"""
ВЫУЧЕННЫЙ СТИЛЬ ПОЛЬЗОВАТЕЛЯ (важно!):
{learned}
"""

        user_info = ""
        if MY_NAMES:
            names_list = ", ".join(MY_NAMES)
            user_info = f"\nИМЕНА ПОЛЬЗОВАТЕЛЯ: {names_list}\nСообщения от любого из этих имён ({names_list}) - это сообщения пользователя, для которого ты пишешь ответ. Остальные - собеседники."

        system_prompt = f"""Ты помощник для написания ответов в Telegram.
Генерируй естественные, уместные ответы на основе контекста переписки.
{user_info}

БАЗОВЫЕ ПРАВИЛА:
{CUSTOM_INSTRUCTIONS}
{style_section}
Отвечай строго в указанном формате, без markdown."""

        # Формируем запрос в зависимости от наличия контекста
        if chat_text:
            user_message = f"""Вот переписка из чата:

{chat_text[-3000:]}

{"Дополнительно: " + custom_prompt if custom_prompt else ""}

Предложи ТРИ РАЗНЫХ варианта ответа. Каждый вариант должен быть оптимальной длины для данной ситуации, но отличаться по подходу, тону или формулировке."""
        else:
            # Режим свободного ввода - без контекста
            user_message = f"""{custom_prompt}

Напиши ТРИ РАЗНЫХ варианта текста по этому запросу. Варианты должны отличаться по подходу или формулировке.

Формат:

[VAR1]
первый вариант
[/VAR1]

[VAR2]
второй вариант (другой подход)
[/VAR2]

[VAR3]
третий вариант (ещё один подход)
[/VAR3]"""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        text = response.content[0].text

        # Парсим варианты
        variants = {"1": "", "2": "", "3": ""}

        import re
        var1_match = re.search(r'\[VAR1\](.*?)\[/VAR1\]', text, re.DOTALL)
        var2_match = re.search(r'\[VAR2\](.*?)\[/VAR2\]', text, re.DOTALL)
        var3_match = re.search(r'\[VAR3\](.*?)\[/VAR3\]', text, re.DOTALL)

        if var1_match:
            variants["1"] = var1_match.group(1).strip()
        if var2_match:
            variants["2"] = var2_match.group(1).strip()
        if var3_match:
            variants["3"] = var3_match.group(1).strip()

        # Если парсинг не удался - возвращаем весь текст как вариант 1
        if not any(variants.values()):
            variants["1"] = text.strip()
            variants["2"] = ""
            variants["3"] = ""

        return variants

    except Exception as e:
        error = f"[ERROR] {str(e)}"
        return {"short": error, "medium": error, "long": error}

def show_window(chat_text=None, free_mode=False):
    """Показывает окно с AI ответом"""
    root = Tk()
    root.title("AI" + (" - Свободный ввод" if free_mode else ""))
    root.geometry("520x420")
    root.minsize(420, 350)

    # Мягкая тёмная тема
    bg = '#1e1e2e'       # Основной фон
    bg2 = '#2a2a3e'      # Карточки
    bg3 = '#363650'      # Поля ввода
    accent = '#a78bfa'   # Фиолетовый акцент
    accent2 = '#7dd3fc'  # Голубой
    accent3 = '#fca5a5'  # Розовый/красный
    text = '#e2e8f0'     # Основной текст
    text2 = '#94a3b8'    # Вторичный текст

    root.configure(bg=bg)

    # Хранилище вариантов
    variants = {"1": "", "2": "", "3": ""}
    current_var = StringVar(value="1")

    # Стили кнопок
    style = ttk.Style()
    style.theme_use('clam')

    # Кнопки вариантов
    style.configure('Var.TButton',
        background=bg3,
        foreground=text,
        font=('Segoe UI', 9),
        padding=(8, 4),
        borderwidth=0
    )
    style.map('Var.TButton', background=[('active', '#4a4a6a')])

    style.configure('VarActive.TButton',
        background=accent,
        foreground='#1e1e2e',
        font=('Segoe UI', 9, 'bold'),
        padding=(8, 4),
        borderwidth=0
    )
    style.map('VarActive.TButton', background=[('active', '#8b5cf6')])

    # Кнопка копировать
    style.configure('Copy.TButton',
        background=accent2,
        foreground='#1e1e2e',
        font=('Segoe UI', 10, 'bold'),
        padding=(16, 8),
        borderwidth=0
    )
    style.map('Copy.TButton', background=[('active', '#38bdf8')])

    # Кнопка перегенерации
    style.configure('Regen.TButton',
        background=bg3,
        foreground=text,
        font=('Segoe UI', 9),
        padding=(12, 8),
        borderwidth=0
    )
    style.map('Regen.TButton', background=[('active', '#4a4a6a')])

    # ==== MAIN CONTAINER ====
    main = Frame(root, bg=bg)
    main.pack(fill='both', expand=True, padx=16, pady=12)

    # ==== Верхняя панель: варианты + уточнение ====
    top_row = Frame(main, bg=bg)
    top_row.pack(fill='x', pady=(0, 10))

    # Кнопки вариантов
    btn_frame = Frame(top_row, bg=bg)
    btn_frame.pack(side='left')

    def update_result_display():
        v = current_var.get()
        result.config(state='normal')
        result.delete('1.0', 'end')
        result.insert('1.0', variants.get(v, ""))

        for btn, num in [(btn_1, '1'), (btn_2, '2'), (btn_3, '3')]:
            if num == v:
                btn.config(style='VarActive.TButton')
            else:
                btn.config(style='Var.TButton')

    def select_var(n):
        current_var.set(n)
        update_result_display()

    btn_1 = ttk.Button(btn_frame, text="1", style='VarActive.TButton', command=lambda: select_var('1'), width=3)
    btn_1.pack(side='left', padx=(0, 4))

    btn_2 = ttk.Button(btn_frame, text="2", style='Var.TButton', command=lambda: select_var('2'), width=3)
    btn_2.pack(side='left', padx=(0, 4))

    btn_3 = ttk.Button(btn_frame, text="3", style='Var.TButton', command=lambda: select_var('3'), width=3)
    btn_3.pack(side='left')

    # Поле уточнения с отступами
    prompt_frame = Frame(top_row, bg=bg3)
    prompt_frame.pack(side='left', fill='x', expand=True, padx=(12, 0))

    prompt_var = StringVar()
    prompt = Entry(
        prompt_frame,
        textvariable=prompt_var,
        bg=bg3,
        fg=text,
        insertbackground=accent,
        font=('Segoe UI', 10),
        relief='flat',
        highlightthickness=0,
        bd=0
    )
    prompt.pack(fill='x', padx=10, pady=8)

    # ==== Область ответа ====
    result = scrolledtext.ScrolledText(
        main,
        bg=bg2,
        fg=text,
        font=('Segoe UI', 11),
        wrap='word',
        relief='flat',
        bd=0,
        padx=14,
        pady=12,
        highlightthickness=0,
        selectbackground=accent,
        selectforeground='#1e1e2e'
    )
    result.pack(fill='both', expand=True, pady=(0, 10))

    # ==== Нижняя панель ====
    bottom = Frame(main, bg=bg)
    bottom.pack(fill='x')

    status_label = Label(
        bottom,
        text="",
        font=('Segoe UI', 9),
        bg=bg,
        fg=text2
    )
    status_label.pack(side='left')

    def set_status(txt, color=None):
        status_label.config(text=txt, fg=color if color else text2)

    def generate():
        nonlocal variants
        p = prompt.get().strip()  # Читаем напрямую из поля

        # В свободном режиме обязателен промпт
        if free_mode and not p:
            set_status("Введи запрос", accent3)
            return

        result.config(state='normal')
        result.delete('1.0', 'end')
        result.insert('1.0', "Генерация..." + (f" ({p[:30]}...)" if p and len(p) > 30 else (f" ({p})" if p else "")))
        set_status("⏳", accent)
        root.update()

        variants = get_ai_replies(chat_text, p)

        # Очищаем поле ввода после генерации
        prompt.delete(0, 'end')

        current_var.set('1')
        update_result_display()

        if variants.get('1', '').startswith('[ERROR]'):
            set_status("Ошибка", accent3)
        else:
            set_status("✓", accent)

    def copy_only():
        txt = result.get('1.0', 'end-1c').strip()
        if txt and "Генерация" not in txt and not txt.startswith('[ERROR]'):
            pyperclip.copy(txt)
            save_to_history(chat_text, txt, current_var.get())
            set_status("Скопировано!", accent2)

    def copy_and_close():
        txt = result.get('1.0', 'end-1c').strip()
        if txt and "Генерация" not in txt and not txt.startswith('[ERROR]'):
            pyperclip.copy(txt)
            save_to_history(chat_text, txt, current_var.get())
            root.destroy()

    # Кнопки
    btn_copy_close = ttk.Button(bottom, text="Скопировать и закрыть", style='Copy.TButton', command=copy_and_close)
    btn_copy_close.pack(side='right')

    btn_copy = ttk.Button(bottom, text="Копия", style='Regen.TButton', command=copy_only)
    btn_copy.pack(side='right', padx=(0, 6))

    btn_regen = ttk.Button(bottom, text="Ещё", style='Regen.TButton', command=generate)
    btn_regen.pack(side='right', padx=(0, 6))

    # Автогенерация при старте (только если есть контекст)
    if not free_mode:
        root.after(100, generate)
    else:
        set_status("Введи запрос и нажми Enter", text2)

    # Горячие клавиши
    def on_enter(e):
        generate()
        return "break"  # Предотвращаем стандартное поведение

    def select_all(e):
        e.widget.select_range(0, 'end')
        e.widget.icursor('end')
        return "break"

    def delete_word_back(e):
        # Ctrl+Backspace - удалить слово назад
        pos = e.widget.index(INSERT)
        text = e.widget.get()
        # Найти начало слова
        i = pos - 1
        while i > 0 and text[i-1] in ' \t':
            i -= 1
        while i > 0 and text[i-1] not in ' \t':
            i -= 1
        e.widget.delete(i, pos)
        return "break"

    def delete_word_forward(e):
        # Ctrl+Delete или Ctrl+Shift+Delete - удалить слово вперед
        pos = e.widget.index(INSERT)
        text = e.widget.get()
        length = len(text)
        # Найти конец слова
        i = pos
        while i < length and text[i] not in ' \t':
            i += 1
        while i < length and text[i] in ' \t':
            i += 1
        e.widget.delete(pos, i)
        return "break"

    prompt.bind('<Return>', on_enter)  # Enter в поле ввода
    prompt.bind('<Control-Key-a>', select_all)  # Ctrl+A - выделить всё
    prompt.bind('<Control-Key-A>', select_all)  # Ctrl+A (caps)
    prompt.bind('<Control-Cyrillic_ef>', select_all)  # Ctrl+Ф (русская раскладка)
    prompt.bind('<Control-BackSpace>', delete_word_back)  # Ctrl+Backspace
    prompt.bind('<Control-Delete>', delete_word_forward)  # Ctrl+Delete
    prompt.bind('<Control-Shift-Delete>', delete_word_forward)  # Ctrl+Shift+Delete

    # Дополнительно: глобальный обработчик Ctrl+A для Entry
    def on_ctrl_a(e):
        if e.widget == prompt:
            prompt.select_range(0, 'end')
            return "break"
    root.bind_all('<Control-a>', on_ctrl_a)
    root.bind_all('<Control-A>', on_ctrl_a)

    root.bind('<Return>', lambda e: generate())  # Enter в окне
    root.bind('<Control-Return>', lambda e: copy_and_close())
    root.bind('<Escape>', lambda e: root.destroy())

    # Окно сверху + фокус на поле ввода
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    prompt.focus_set()  # Фокус на поле уточнения для голосового ввода

    root.mainloop()

def on_f9():
    """Обработчик F9 - ответ на контекст"""
    print("[F9] Reply mode")

    text = get_clipboard()

    if not text or len(text.strip()) < 3:
        print("[!] Bufer pust")
        messagebox.showinfo("AI Overlay", "Skopiruyte tekst (Ctrl+C) pered F9")
        return

    print(f"[OK] {len(text)} chars")
    show_window(chat_text=text, free_mode=False)

def on_f8():
    """Обработчик F8 - свободный ввод"""
    print("[F8] Free mode")
    show_window(chat_text=None, free_mode=True)

if __name__ == "__main__":
    try:
        keyboard.add_hotkey('f9', on_f9)
        keyboard.add_hotkey('f8', on_f8)
        print("[*] Ozhidayu F8/F9...\n")
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[OK] Ostanovleno")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
