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

# Claude API
import os
from dotenv import load_dotenv
load_dotenv()
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
CLAUDE_MODEL = "claude-sonnet-4-5"

# Файлы
BASE_DIR = Path(__file__).parent
INSTRUCTIONS_FILE = BASE_DIR / "custom_instructions.txt"
HISTORY_FILE = BASE_DIR / "style_history.json"
LEARNED_STYLE_FILE = BASE_DIR / "learned_style.txt"

# Загружаем правила стиля
try:
    CUSTOM_INSTRUCTIONS = INSTRUCTIONS_FILE.read_text(encoding='utf-8')
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
print("\n1. Vydelite tekst v AyuGram")
print("2. Nazhmite Ctrl+C")
print("3. Nazhmite F9")
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

        system_prompt = f"""Ты помощник для написания ответов в Telegram.
Генерируй естественные, уместные ответы на основе контекста переписки.

БАЗОВЫЕ ПРАВИЛА:
{CUSTOM_INSTRUCTIONS}
{style_section}
Отвечай строго в указанном формате, без markdown."""

        user_message = f"""Вот переписка из чата:

{chat_text[-3000:]}

{"Дополнительно: " + custom_prompt if custom_prompt else ""}

Предложи ТРИ варианта ответа в формате:

[SHORT]
краткий ответ (1-2 предложения)
[/SHORT]

[MEDIUM]
средний ответ (2-4 предложения)
[/MEDIUM]

[LONG]
развёрнутый ответ (4-6 предложений)
[/LONG]"""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        text = response.content[0].text

        # Парсим варианты
        variants = {"short": "", "medium": "", "long": ""}

        import re
        short_match = re.search(r'\[SHORT\](.*?)\[/SHORT\]', text, re.DOTALL)
        medium_match = re.search(r'\[MEDIUM\](.*?)\[/MEDIUM\]', text, re.DOTALL)
        long_match = re.search(r'\[LONG\](.*?)\[/LONG\]', text, re.DOTALL)

        if short_match:
            variants["short"] = short_match.group(1).strip()
        if medium_match:
            variants["medium"] = medium_match.group(1).strip()
        if long_match:
            variants["long"] = long_match.group(1).strip()

        # Если парсинг не удался - возвращаем весь текст как medium
        if not any(variants.values()):
            variants["medium"] = text.strip()
            variants["short"] = text.strip()[:100] + "..." if len(text) > 100 else text.strip()
            variants["long"] = text.strip()

        return variants

    except Exception as e:
        error = f"[ERROR] {str(e)}"
        return {"short": error, "medium": error, "long": error}

def show_window(chat_text):
    """Показывает стильное окно с AI ответом"""
    root = Tk()
    root.title("AI Reply")
    root.geometry("700x580")
    root.minsize(550, 450)
    root.configure(bg='#0d0d12')

    # Цвета
    bg = '#0d0d12'
    bg2 = '#1a1a24'
    pink = '#ff3399'
    cyan = '#00ccff'
    orange = '#ff9933'
    gray = '#666666'
    white = '#ffffff'

    # Хранилище вариантов
    variants = {"short": "", "medium": "", "long": ""}
    current_type = StringVar(value="medium")

    # Стиль для ttk
    style = ttk.Style()
    style.theme_use('clam')

    for name, color, hover in [
        ('Pink.TButton', pink, '#dd2277'),
        ('Cyan.TButton', cyan, '#00aadd'),
        ('Orange.TButton', orange, '#dd7722'),
        ('Gray.TButton', '#444455', '#555566')
    ]:
        style.configure(name,
            background=color,
            foreground='#000000',
            font=('Segoe UI', 10, 'bold'),
            padding=(12, 8),
            borderwidth=0
        )
        style.map(name, background=[('active', hover)])

    # ==== HEADER ====
    header = Frame(root, bg=bg, height=50)
    header.pack(fill='x', side='top')
    header.pack_propagate(False)

    Label(
        header,
        text="AI REPLY",
        font=('Segoe UI', 14, 'bold'),
        bg=bg,
        fg=cyan
    ).pack(pady=12)

    # ==== FOOTER ====
    footer = Frame(root, bg=bg2, height=60)
    footer.pack(fill='x', side='bottom')
    footer.pack_propagate(False)

    status_label = Label(
        footer,
        text="",
        font=('Segoe UI', 9),
        bg=bg2,
        fg=gray
    )
    status_label.pack(side='left', padx=15, pady=15)

    # ==== MAIN ====
    main = Frame(root, bg=bg)
    main.pack(fill='both', expand=True, padx=18, pady=8)

    # Контекст (компактный)
    ctx_frame = Frame(main, bg=bg)
    ctx_frame.pack(fill='x', pady=(0, 8))

    Label(ctx_frame, text="КОНТЕКСТ", font=('Segoe UI', 8), bg=bg, fg=gray).pack(side='left')

    context = Entry(
        ctx_frame,
        bg=bg2,
        fg='#666666',
        font=('Consolas', 8),
        relief='flat',
        state='readonly'
    )
    context.pack(side='left', fill='x', expand=True, padx=(8, 0), ipady=4)
    context.config(state='normal')
    context.insert(0, chat_text[-100:].replace('\n', ' '))
    context.config(state='readonly')

    # Уточнение
    prompt_frame = Frame(main, bg=bg)
    prompt_frame.pack(fill='x', pady=(0, 10))

    Label(prompt_frame, text="УТОЧНЕНИЕ", font=('Segoe UI', 8), bg=bg, fg=gray).pack(side='left')

    prompt_var = StringVar()
    prompt = Entry(
        prompt_frame,
        textvariable=prompt_var,
        bg=bg2,
        fg=white,
        insertbackground=cyan,
        font=('Segoe UI', 10),
        relief='flat',
        highlightthickness=1,
        highlightbackground=cyan,
        highlightcolor=cyan
    )
    prompt.pack(side='left', fill='x', expand=True, padx=(8, 0), ipady=6)

    # Варианты ответа - кнопки переключения
    variant_frame = Frame(main, bg=bg)
    variant_frame.pack(fill='x', pady=(0, 8))

    Label(variant_frame, text="ВАРИАНТ", font=('Segoe UI', 8), bg=bg, fg=gray).pack(side='left')

    btn_vars = Frame(variant_frame, bg=bg)
    btn_vars.pack(side='left', padx=(8, 0))

    def update_result_display():
        t = current_type.get()
        result.config(state='normal')
        result.delete('1.0', 'end')
        result.insert('1.0', variants.get(t, ""))
        result.config(state='normal')

        # Обновляем стиль кнопок
        for btn, typ in [(btn_short, 'short'), (btn_medium, 'medium'), (btn_long, 'long')]:
            if typ == t:
                btn.config(style='Pink.TButton')
            else:
                btn.config(style='Gray.TButton')

    def select_short():
        current_type.set('short')
        update_result_display()

    def select_medium():
        current_type.set('medium')
        update_result_display()

    def select_long():
        current_type.set('long')
        update_result_display()

    btn_short = ttk.Button(btn_vars, text="Кратко", style='Gray.TButton', command=select_short)
    btn_short.pack(side='left', padx=2)

    btn_medium = ttk.Button(btn_vars, text="Средне", style='Pink.TButton', command=select_medium)
    btn_medium.pack(side='left', padx=2)

    btn_long = ttk.Button(btn_vars, text="Подробно", style='Gray.TButton', command=select_long)
    btn_long.pack(side='left', padx=2)

    # Ответ
    Label(main, text="ОТВЕТ", font=('Segoe UI', 9, 'bold'), bg=bg, fg=pink, anchor='w').pack(fill='x', pady=(0, 3))

    result = scrolledtext.ScrolledText(
        main,
        bg=bg2,
        fg=white,
        font=('Segoe UI', 11),
        wrap='word',
        relief='flat',
        bd=0,
        padx=12,
        pady=10,
        highlightthickness=2,
        highlightbackground=pink,
        highlightcolor=pink
    )
    result.pack(fill='both', expand=True)

    def set_status(text, color=gray):
        status_label.config(text=text, fg=color)

    def generate():
        nonlocal variants
        p = prompt_var.get().strip()

        result.config(state='normal')
        result.delete('1.0', 'end')
        result.insert('1.0', "Генерация 3 вариантов...")
        set_status("Ожидание ответа...", cyan)
        root.update()

        variants = get_ai_replies(chat_text, p)

        current_type.set('medium')
        update_result_display()

        if variants.get('medium', '').startswith('[ERROR]'):
            set_status("Ошибка API", '#ff4444')
        else:
            set_status("Готово! Выбери вариант и скопируй", pink)

    def copy_and_close():
        text = result.get('1.0', 'end-1c').strip()
        if text and "Генерация" not in text and not text.startswith('[ERROR]'):
            pyperclip.copy(text)
            # Сохраняем в историю для обучения
            save_to_history(chat_text, text, current_type.get())
            root.destroy()

    # Кнопки footer
    btn_copy = ttk.Button(footer, text="СКОПИРОВАТЬ", style='Cyan.TButton', command=copy_and_close)
    btn_copy.pack(side='right', padx=12, pady=10)

    btn_regen = ttk.Button(footer, text="ДРУГОЙ", style='Orange.TButton', command=generate)
    btn_regen.pack(side='right', padx=5, pady=10)

    # Автогенерация
    root.after(100, generate)

    # Горячие клавиши
    root.bind('<Return>', lambda e: generate())
    root.bind('<Control-Return>', lambda e: copy_and_close())
    root.bind('<Escape>', lambda e: root.destroy())
    root.bind('1', lambda e: select_short())
    root.bind('2', lambda e: select_medium())
    root.bind('3', lambda e: select_long())

    # Окно сверху
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()

    root.mainloop()

def on_hotkey():
    """Обработчик F9"""
    print("[F9]")

    text = get_clipboard()

    if not text or len(text.strip()) < 3:
        print("[!] Bufer pust")
        messagebox.showinfo("AI Overlay", "Skopiruyte tekst (Ctrl+C) pered F9")
        return

    print(f"[OK] {len(text)} chars")
    show_window(text)

if __name__ == "__main__":
    try:
        keyboard.add_hotkey('f9', on_hotkey)
        print("[*] Ozhidayu F9...\n")
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[OK] Ostanovleno")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
