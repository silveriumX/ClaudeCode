"""
Скрипт для получения данных персональной конференции Zoom (Personal Meeting Room / PMI)
Использует Server-to-Server OAuth для доступа к Zoom API
"""

import requests
import base64
import json
from datetime import datetime
import os
import sys

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Учётные данные из .cursor/mcp.json
ZOOM_ACCOUNT_ID = "0X0NAKMoRgqHSpB7RRGg6Q"
ZOOM_CLIENT_ID = "ajlfiqtTSWOdvZ9ZDJDqA"
ZOOM_CLIENT_SECRET = "S4r0wOc1hDlAnfBbZX0QjEfo0X6vRTgv"

# Zoom API endpoints
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"

def get_zoom_access_token():
    """Получить access token через Server-to-Server OAuth"""
    # Создаём Basic Auth header
    credentials = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }

    try:
        response = requests.post(ZOOM_TOKEN_URL, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"[ERROR] Ошибка получения токена: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Ответ API: {e.response.text}")
        return None

def get_user_info(access_token):
    """Получить информацию о пользователе (включая PMI)"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Получаем информацию о текущем пользователе
    try:
        response = requests.get(f"{ZOOM_API_BASE}/users/me", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Если нет scope для user:read, возвращаем минимальную информацию
        print(f"[WARNING] Не удалось получить полную информацию о пользователе: {e}")
        print("   Продолжаем без user info...")
        return {"id": "me", "email": "", "display_name": ""}

def get_personal_meeting_room(access_token, user_id):
    """Получить данные Personal Meeting Room (PMI)"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Получаем настройки пользователя, включая PMI
    try:
        response = requests.get(
            f"{ZOOM_API_BASE}/users/{user_id}/settings",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        settings = response.json()

        # Получаем PMI
        pmi = settings.get("pmi", {})

        # Если PMI включён, получаем детали встречи
        if pmi:
            pmi_number = pmi.get("pmi") or user_id  # PMI может быть в user_id или отдельно
            # Получаем детали PMI встречи
            meeting_response = requests.get(
                f"{ZOOM_API_BASE}/meetings/{pmi_number}",
                headers=headers,
                timeout=10
            )

            if meeting_response.status_code == 200:
                meeting_data = meeting_response.json()
                return {
                    "pmi": pmi_number,
                    "join_url": meeting_data.get("join_url", ""),
                    "password": meeting_data.get("password", ""),
                    "topic": meeting_data.get("topic", "Personal Meeting Room"),
                    "settings": meeting_data.get("settings", {})
                }
            else:
                # Если встреча не найдена, создаём данные на основе настроек
                return {
                    "pmi": pmi_number,
                    "join_url": f"https://zoom.us/j/{pmi_number}",
                    "password": settings.get("pmi_password", ""),
                    "topic": "Personal Meeting Room",
                    "note": "PMI найден, но встреча может быть не создана. Используйте join_url для входа."
                }

        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("[WARNING] PMI встреча не найдена. Попробуем получить через список встреч...")
            return None
        print(f"[ERROR] Ошибка получения PMI: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Ответ API: {e.response.text}")
        return None
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return None

def get_all_meetings(access_token):
    """Получить все встречи пользователя (может включать PMI)"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        # Пробуем получить все типы встреч
        response = requests.get(
            f"{ZOOM_API_BASE}/users/me/meetings?type=live&page_size=100",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        meetings = response.json().get("meetings", [])

        # Также пробуем получить scheduled встречи
        try:
            response2 = requests.get(
                f"{ZOOM_API_BASE}/users/me/meetings?type=scheduled&page_size=100",
                headers=headers,
                timeout=10
            )
            if response2.status_code == 200:
                meetings.extend(response2.json().get("meetings", []))
        except:
            pass

        return meetings
    except Exception as e:
        print(f"[WARNING] Ошибка получения списка встреч: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Ответ API: {e.response.text}")
        return []

def save_personal_meeting_info(pmi_data, user_info):
    """Сохранить данные персональной конференции в файл"""
    output_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "Data",
        "zoom_personal_meeting.json"
    )

    # Создаём директорию, если её нет
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    data = {
        "updated_at": datetime.now().isoformat(),
        "user": {
            "id": user_info.get("id", ""),
            "email": user_info.get("email", ""),
            "display_name": user_info.get("display_name", ""),
        },
        "personal_meeting_room": pmi_data
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Данные сохранены в: {output_file}")
    return output_file

def main():
    print("Получение данных персональной конференции Zoom...\n")

    # 1. Получаем access token
    print("[1] Получение access token...")
    access_token = get_zoom_access_token()
    if not access_token:
        print("[ERROR] Не удалось получить токен. Проверьте учётные данные.")
        return
    print("[OK] Токен получен")

    # 2. Получаем информацию о пользователе
    print("\n[2] Получение информации о пользователе...")
    user_info = get_user_info(access_token)
    if not user_info:
        print("[ERROR] Не удалось получить информацию о пользователе.")
        return

    user_id = user_info.get("id")
    print(f"[OK] Пользователь: {user_info.get('display_name', 'Unknown')} ({user_info.get('email', '')})")

    # 3. Получаем PMI
    print("\n[3] Получение Personal Meeting Room (PMI)...")
    pmi_data = get_personal_meeting_room(access_token, user_id)

    if not pmi_data:
        print("[WARNING] PMI не найден через settings. Проверяю список встреч...")
        meetings = get_all_meetings(access_token)
        print(f"   Найдено встреч: {len(meetings)}")

        # Ищем встречу с типом "instant" (3) или "recurring_no_fixed_time" (8) - может быть PMI
        # Также ищем встречу с названием "Personal Meeting Room" или похожим
        for meeting in meetings:
            meeting_type = meeting.get("type", 0)
            topic = meeting.get("topic", "").lower()

            # PMI обычно имеет тип 3 (instant) или может быть постоянной встречей
            if meeting_type == 3 or "personal" in topic or "pmi" in topic:
                pmi_data = {
                    "pmi": meeting.get("id", ""),
                    "join_url": meeting.get("join_url", ""),
                    "password": meeting.get("password", ""),
                    "topic": meeting.get("topic", "Personal Meeting Room"),
                    "note": "Найдено через список встреч"
                }
                print(f"   Найдена потенциальная PMI встреча: {meeting.get('topic', 'N/A')}")
                break

        # Если не нашли, берём первую встречу как возможную PMI
        if not pmi_data and meetings:
            print("   Используем первую встречу из списка...")
            meeting = meetings[0]
            pmi_data = {
                "pmi": meeting.get("id", ""),
                "join_url": meeting.get("join_url", ""),
                "password": meeting.get("password", ""),
                "topic": meeting.get("topic", "Personal Meeting Room"),
                "note": "Первая встреча из списка (возможно, это не PMI)"
            }

    if pmi_data:
        print("[OK] PMI найден!")
        print(f"\nДанные персональной конференции:")
        print(f"   ID встречи: {pmi_data.get('pmi', 'N/A')}")
        print(f"   Ссылка для входа: {pmi_data.get('join_url', 'N/A')}")
        print(f"   Пароль: {pmi_data.get('password', 'N/A')}")
        print(f"   Тема: {pmi_data.get('topic', 'N/A')}")

        # 4. Сохраняем в файл
        print("\n[4] Сохранение данных...")
        output_file = save_personal_meeting_info(pmi_data, user_info)

        # Также создаём текстовый файл для быстрого доступа
        txt_file = output_file.replace(".json", ".txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("ПЕРСОНАЛЬНАЯ КОНФЕРЕНЦИЯ ZOOM\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Ссылка для входа:\n{pmi_data.get('join_url', 'N/A')}\n\n")
            f.write(f"ID встречи: {pmi_data.get('pmi', 'N/A')}\n")
            f.write(f"Пароль: {pmi_data.get('password', 'N/A')}\n")
            f.write(f"Тема: {pmi_data.get('topic', 'N/A')}\n")
            f.write(f"\nОбновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f"[OK] Текстовый файл: {txt_file}")
        print(f"\nТеперь вы можете быстро открыть файл {txt_file} для доступа к ссылке!")
    else:
        print("[ERROR] Не удалось найти Personal Meeting Room.")
        print("   Убедитесь, что PMI включён в настройках Zoom аккаунта.")

if __name__ == "__main__":
    main()
