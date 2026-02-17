# ApiTools Proxima — прокси для исходящих запросов

**Тип:** HTTP/SOCKS5 прокси (не API управления пакетами).
**Отличие от Proxyma:** Proxyma в репозитории — это API для учёта пакетов/трафика; ApiTools Proxima — готовый прокси-сервер для подстановки в `requests`, `httpx`, curl.

---

## Параметры подключения

Хранить в `.env` (не в коде):

```env
# ApiTools Proxima
APITOOLS_PROXIMA_HOST=185.162.130.86
APITOOLS_PROXIMA_HTTP_PORT=10147
APITOOLS_PROXIMA_HTTPS_PORT=10494
APITOOLS_PROXIMA_SOCKS5_PORT=10761
APITOOLS_PROXIMA_LOGIN=...
APITOOLS_PROXIMA_PASSWORD=...
```

URL для подстановки в клиенты:

- **HTTP/HTTPS прокси:** `http://LOGIN:PASSWORD@HOST:10494`
- **SOCKS5:** `socks5://LOGIN:PASSWORD@HOST:10761`

---

## Возможности

| Функция | Синтаксис в логине | Пример |
|--------|---------------------|--------|
| Страна (ISO 3166-1 alpha-2) | `xxx_c_US` | США |
| Город (пробел → `-`) | `xxx_city_Paris` | Париж |
| Sticky session (один IP на сессию) | `xxx_s_mySes1` | Сессия `mySes1` |
| В связке | все параметры вместе | `xxx_c_US_city_New-York_s_mySes1` |

---

## Использование

### Curl

```bash
# Базовый
curl -x "http://LOGIN:PASSWORD@185.162.130.86:10494" https://ipinfo.io

# США, Нью-Йорк, одна сессия
curl -x "http://LOGIN_c_US_city_New-York_s_mySes1:PASSWORD@185.162.130.86:10494" https://ipinfo.io
```

### Python (requests)

```python
import os

proxies = {
    "http": os.environ["APITOOLS_PROXIMA_HTTP_URL"],
    "https": os.environ["APITOOLS_PROXIMA_HTTP_URL"],
}
r = requests.get("https://ipinfo.io", proxies=proxies, timeout=30)
```

### Python (httpx)

```python
import httpx
import os

with httpx.Client(proxy=os.environ["APITOOLS_PROXIMA_HTTP_URL"]) as client:
    r = client.get("https://ipinfo.io")
```

---

## Где полезно в вашем репозитории

1. **ResearchSystem** — ресерч через EXA/другие источники с другим IP или гео (страна/город), снижение риска rate limit.
2. **Скрипты с requests/httpx** — парсинг, проверки доступности с выхода из нужной страны.
3. **Тестирование** — как сайт видит запрос из US/FR и т.д.
4. **Резерв/альтернатива** — отдельный провайдер от Proxyma (Proxyma — учёт пакетов; ApiTools — сам трафик).

---

## Безопасность

- Учётные данные хранить только в `.env`, не коммитить в репозиторий.
- В `.env.example` указать только имена переменных без значений.
