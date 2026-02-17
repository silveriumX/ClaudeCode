"""
DocChat - Локальный ассистент с Claude для работы с документами
"""

import streamlit as st
import anthropic
from pathlib import Path
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем процессоры
from processors import process_pdf, process_excel, process_word, process_image

# Конфигурация страницы
st.set_page_config(
    page_title="DocChat",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные стили
st.markdown("""
<style>
    /* Основные стили */
    .main {
        padding: 1rem 2rem;
    }

    /* Заголовок */
    .title-container {
        text-align: center;
        padding: 1rem 0 2rem 0;
    }

    /* Область загрузки файлов */
    .uploadedFile {
        border: 2px dashed #4A90D9;
        border-radius: 10px;
        padding: 20px;
        background-color: #f8f9fa;
    }

    /* Сообщения чата */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }

    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }

    /* Файлы */
    .file-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background-color: #e8f5e9;
        border-radius: 15px;
        margin: 0.25rem;
        font-size: 0.85rem;
    }

    /* Кнопки */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Инициализация состояния сессии"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "documents" not in st.session_state:
        st.session_state.documents = {}  # filename -> processed content
    if "client" not in st.session_state:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            st.session_state.client = anthropic.Anthropic(api_key=api_key)
        else:
            st.session_state.client = None


def get_file_icon(filename: str) -> str:
    """Возвращает иконку для типа файла"""
    ext = filename.lower().split('.')[-1]
    icons = {
        'pdf': '📕',
        'xlsx': '📊',
        'xls': '📊',
        'docx': '📘',
        'doc': '📘',
        'png': '🖼️',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'gif': '🖼️',
        'webp': '🖼️'
    }
    return icons.get(ext, '📄')


def process_uploaded_file(uploaded_file) -> dict:
    """Обрабатывает загруженный файл"""
    filename = uploaded_file.name
    file_bytes = uploaded_file.read()
    ext = filename.lower().split('.')[-1]

    if ext == 'pdf':
        return process_pdf(file_bytes, filename)
    elif ext in ['xlsx', 'xls']:
        return process_excel(file_bytes, filename)
    elif ext in ['docx', 'doc']:
        return process_word(file_bytes, filename)
    elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']:
        return process_image(file_bytes, filename)
    else:
        return {
            "filename": filename,
            "type": "unknown",
            "text": f"[Неподдерживаемый формат файла: {ext}]"
        }


def build_messages_for_api(user_message: str, documents: dict) -> list:
    """Собирает сообщения для API с учетом документов"""

    # Системное сообщение с контекстом документов
    system_parts = ["Ты - полезный ассистент, работающий с документами пользователя."]

    if documents:
        system_parts.append("\n\n## Загруженные документы:\n")
        for filename, doc_data in documents.items():
            if doc_data.get("text"):
                system_parts.append(f"### {filename}\n")
                system_parts.append(doc_data["text"][:50000])  # Лимит на документ
                system_parts.append("\n---\n")

    system_message = "\n".join(system_parts)

    # Собираем историю сообщений
    messages = []
    for msg in st.session_state.messages:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Добавляем текущее сообщение
    # Проверяем, есть ли изображения для Vision API
    content = []

    # Добавляем изображения из документов
    for filename, doc_data in documents.items():
        if doc_data.get("image_data"):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": doc_data["image_data"]["media_type"],
                    "data": doc_data["image_data"]["base64"]
                }
            })
        elif doc_data.get("images"):
            # PDF как изображения
            for img in doc_data["images"][:10]:  # Максимум 10 страниц
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img["media_type"],
                        "data": img["base64"]
                    }
                })

    # Добавляем текст сообщения
    content.append({
        "type": "text",
        "text": user_message
    })

    messages.append({
        "role": "user",
        "content": content if len(content) > 1 else user_message
    })

    return system_message, messages


def send_message(user_message: str):
    """Отправляет сообщение в Claude API"""
    if not st.session_state.client:
        st.error("❌ API ключ не настроен. Проверьте файл .env")
        return

    # Добавляем сообщение пользователя в историю
    st.session_state.messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        system_message, messages = build_messages_for_api(
            user_message,
            st.session_state.documents
        )

        # Вызов API
        with st.spinner("Claude думает..."):
            response = st.session_state.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_message,
                messages=messages
            )

        assistant_message = response.content[0].text

        # Добавляем ответ в историю
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

    except Exception as e:
        st.error(f"❌ Ошибка API: {e}")
        # Удаляем сообщение пользователя при ошибке
        st.session_state.messages.pop()


def main():
    """Основная функция приложения"""
    init_session_state()

    # Заголовок
    st.markdown("""
    <div class="title-container">
        <h1>📄 DocChat</h1>
        <p style="color: #666;">Локальный ассистент с Claude для работы с документами</p>
    </div>
    """, unsafe_allow_html=True)

    # Боковая панель
    with st.sidebar:
        st.header("📎 Документы")

        # Загрузка файлов
        uploaded_files = st.file_uploader(
            "Загрузите файлы",
            type=['pdf', 'xlsx', 'xls', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'webp'],
            accept_multiple_files=True,
            help="Поддерживаются: PDF, Excel, Word, изображения"
        )

        # Обработка загруженных файлов
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state.documents:
                    with st.spinner(f"Обработка {uploaded_file.name}..."):
                        processed = process_uploaded_file(uploaded_file)
                        st.session_state.documents[uploaded_file.name] = processed

        # Показываем загруженные документы
        if st.session_state.documents:
            st.markdown("---")
            st.subheader("Загруженные файлы:")
            for filename, doc_data in st.session_state.documents.items():
                icon = get_file_icon(filename)
                doc_type = doc_data.get("type", "unknown")

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{icon} **{filename}**")
                    if doc_data.get("pages"):
                        st.caption(f"📄 {doc_data['pages']} стр.")
                    if doc_data.get("sheets"):
                        st.caption(f"📊 {len(doc_data['sheets'])} листов")
                with col2:
                    if st.button("🗑️", key=f"del_{filename}"):
                        del st.session_state.documents[filename]
                        st.rerun()

            # Кнопка очистки всех документов
            if st.button("🗑️ Очистить все", use_container_width=True):
                st.session_state.documents = {}
                st.rerun()

        st.markdown("---")

        # Настройки
        st.header("⚙️ Настройки")

        # Проверка API
        if st.session_state.client:
            st.success("✅ API подключен")
        else:
            st.error("❌ API не настроен")
            st.info("Создайте файл .env с ANTHROPIC_API_KEY")

        # Кнопка очистки чата
        if st.button("🔄 Новый чат", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Основная область - чат
    chat_container = st.container()

    with chat_container:
        # Отображаем историю сообщений
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])

    # Поле ввода
    if prompt := st.chat_input("Введите сообщение..."):
        # Показываем сообщение пользователя сразу
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Отправляем и получаем ответ
        send_message(prompt)

        # Показываем ответ
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(st.session_state.messages[-1]["content"])

        st.rerun()

    # Подсказки если нет документов
    if not st.session_state.documents and not st.session_state.messages:
        st.markdown("---")
        st.info("""
        👋 **Добро пожаловать в DocChat!**

        1. Загрузите документы через боковую панель слева
        2. Задайте вопрос о содержимом документов
        3. Claude проанализирует и ответит

        **Поддерживаемые форматы:** PDF, Excel (.xlsx), Word (.docx), изображения
        """)


if __name__ == "__main__":
    main()
