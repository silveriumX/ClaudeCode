# VPN-протоколы: что мощнее VLESS и устойчивее к блокировкам

**Дата:** 09.02.2026
**Цель:** Найти протокол для своего VPS (Ubuntu), максимально устойчивый к блокировкам DPI

---

## Executive Summary

**Короткий ответ:** VLESS сам по себе -- это просто протокол. "Мощь" дает комбинация **VLESS + REALITY + XHTTP** на движке **Xray-core**. Это на сегодня **самый устойчивый к блокировкам стек** в мире. Как резервный канал -- **Hysteria2** (быстрый, но проще блокируется).

**Рекомендация: поставить 3X-UI панель с двумя протоколами одновременно:**
1. **VLESS + XTLS-Vision + REALITY** (основной, TCP) -- неотличим от обычного HTTPS
2. **Hysteria2** (резервный, UDP/QUIC) -- максимальная скорость на плохих линиях

---

## Сравнительная таблица протоколов

| Протокол | Транспорт | Устойчивость к DPI | Скорость | Сложность настройки | Статус в 2026 |
|---|---|---|---|---|---|
| **VLESS + REALITY** | TCP | ***** (максимум) | **** | Средняя | Золотой стандарт |
| **VLESS + XHTTP + REALITY** | TCP split | ***** (максимум) | **** | Высокая | Новейший, экспериментальный |
| **Hysteria2** | UDP/QUIC | *** | ***** (максимум) | Простая | Быстро, но блокируется по UDP |
| **TUIC v5** | UDP/QUIC | *** | **** | Средняя | Менее популярен чем Hy2 |
| **Shadowsocks 2022** | TCP | **** | **** | Простая | Надежный, проверенный |
| **Trojan** | TCP/TLS | **** | **** | Средняя | Стабильный |
| **WireGuard** | UDP | * | ***** | Простая | Легко блокируется DPI |
| **OpenVPN** | TCP/UDP | * | *** | Средняя | Легко детектируется |

---

## Детальный анализ топ-протоколов

### 1. VLESS + XTLS-Vision + REALITY (рекомендация #1)

**Почему это лучшее:**
- **REALITY** выполняет настоящий TLS-хендшейк с реальным сайтом (например google.com)
- Для DPI/файрвола трафик **неотличим** от обычного посещения этого сайта
- Не нужен свой домен и SSL-сертификат
- **XTLS-Vision** убирает избыточное шифрование (TLS-in-TLS), снижая нагрузку на CPU
- Работает даже при SNI-whitelist блокировке (как в Китае и Иране)

**Принцип работы REALITY:**
1. Клиент отправляет TLS ClientHello с SNI легитимного сайта (напр. `www.microsoft.com`)
2. Сервер проверяет клиента по криптографическому ключу (ECDH + HMAC)
3. Если клиент свой -- устанавливается прокси-соединение
4. Если клиент чужой (проверяющий) -- запрос проксируется на **настоящий сайт**
5. DPI видит только нормальный HTTPS-трафик к microsoft.com

**Как блокируют:**
- Пока не научились надежно блокировать
- В Иране MCI пытался блокировать по IP (а не по протоколу)
- В Китае GFW пока не блокирует REALITY

### 2. VLESS + XHTTP + REALITY (новейший, 2025+)

**Что нового:**
- Разделение upstream (отправка) и downstream (получение) трафика
- Upstream может идти по IPv4 TCP, downstream по IPv6 UDP
- GFW не может сопоставить два потока и определить что это прокси
- "Stream-up mode" -- трафик разбивается на разные каналы

**Статус:** Экспериментальный, но уже работает в Xray-core. Подходит для продвинутых пользователей.

### 3. Hysteria2 (рекомендация #2 -- резервный)

**Плюсы:**
- Работает поверх QUIC/UDP -- значительно быстрее на плохих линиях
- Встроенная обфускация (Salamander)
- Простая настройка
- Отличная скорость на "мусорных" VPS с плохим пингом

**Минусы:**
- UDP-трафик легко выделяется DPI
- В Китае GFW уже научился распознавать и блокировать Hy2 по профилю трафика
- Некоторые провайдеры в России блокируют нестандартный UDP
- Большой объем UDP-трафика может быть классифицирован как DDoS

**Вывод:** Использовать как **резервный** канал. Если REALITY заблокируют (маловероятно), переключаться на Hy2, и наоборот.

### 4. Shadowsocks 2022 (AEAD 2022)

**Плюсы:**
- Проверенный временем, стабильный
- Новые шифры `2022-blake3-aes-128-gcm` сложнее детектировать
- Поддержка мультиплексирования в sing-box

**Минусы:**
- Менее стелсный чем REALITY (трафик все же отличается от обычного HTTPS)
- GFW уже умеет частично блокировать

---

## Практическая инструкция: установка на Ubuntu VPS

### Вариант A: 3X-UI панель (рекомендуется -- удобно)

3X-UI -- веб-панель для управления Xray-core. Поддерживает VLESS, Reality, Hysteria2, Trojan, Shadowsocks, WireGuard.

#### Шаг 1: Подготовка VPS

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка необходимого
apt install -y curl wget

# Включение BBR (ускорение TCP)
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
sysctl -p

# Проверка BBR
sysctl net.ipv4.tcp_congestion_control
# Должно показать: net.ipv4.tcp_congestion_control = bbr
```

#### Шаг 2: Установка 3X-UI

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

После установки скрипт выдаст:
- URL панели (обычно `http://YOUR_IP:2053`)
- Логин и пароль

**Важно:** Сразу после установки:
1. Зайти в панель
2. Сменить пароль
3. Сменить порт панели на нестандартный
4. Настроить HTTPS для панели (опционально, но рекомендуется)

#### Шаг 3: Создание VLESS + REALITY inbound

В панели 3X-UI:

1. **Inbounds** -> **Add Inbound**
2. Настройки:
   - **Protocol:** VLESS
   - **Port:** 443
   - **Flow:** `xtls-rprx-vision`
   - **Security:** Reality
   - **uTLS:** `chrome` (или `firefox`)
   - **Dest (target):** `www.microsoft.com:443` (любой популярный сайт с TLSv1.3 + H2)
   - **SNI:** `www.microsoft.com`
   - Нажать **Get New Cert** для генерации ключей

3. Добавить клиента (пользователя)
4. Скопировать ссылку для подключения (QR код)

#### Шаг 4: Создание Hysteria2 inbound (резервный)

1. **Inbounds** -> **Add Inbound**
2. Настройки:
   - **Protocol:** Hysteria2
   - **Port:** любой (напр. 8443)
   - **Obfuscation:** Salamander + пароль
   - **TLS:** Самоподписанный сертификат (панель сгенерирует)

#### Шаг 5: Клиенты для подключения

| Платформа | Клиент | Ссылка |
|---|---|---|
| **Windows** | Hiddify Next, v2rayN, Nekoray | github.com/hiddify/hiddify-app |
| **Android** | Hiddify Next, v2rayNG | Play Store / GitHub |
| **iOS** | Hiddify, Shadowrocket, Streisand | App Store |
| **macOS** | Hiddify Next, V2Box | GitHub |
| **Linux** | Hiddify Next, Nekoray | GitHub |

**Hiddify Next** -- универсальный клиент, поддерживает все протоколы, кроссплатформенный.

---

### Вариант B: Ручная установка Xray-core (для продвинутых)

#### Шаг 1: Установка Xray

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

#### Шаг 2: Генерация ключей

```bash
# UUID
xray uuid

# X25519 ключевая пара
xray x25519

# Short ID (случайный hex)
openssl rand -hex 8
```

#### Шаг 3: Конфигурация `/usr/local/etc/xray/config.json`

```json
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "ВАШ-UUID",
            "flow": "xtls-rprx-vision"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "www.microsoft.com:443",
          "xver": 0,
          "serverNames": [
            "www.microsoft.com"
          ],
          "privateKey": "ВАШ-PRIVATE-KEY",
          "shortIds": [
            "ВАШ-SHORT-ID"
          ]
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    }
  ]
}
```

#### Шаг 4: Запуск

```bash
systemctl enable xray
systemctl start xray
systemctl status xray
```

---

### Вариант C: sing-box (мульти-протокол через один движок)

sing-box поддерживает все протоколы в одном конфиге. Скрипт от 233boy:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/233boy/sing-box/main/install.sh)
```

После установки:
```bash
sb add reality   # Добавить VLESS+Reality
sb add hy        # Добавить Hysteria2
sb add ss        # Добавить Shadowsocks 2022
```

---

## Стратегия максимальной устойчивости

### Принцип: "Несколько протоколов + быстрое переключение"

```
                        [Ваш VPS Ubuntu]
                              |
              +---------------+---------------+
              |               |               |
        [VLESS+REALITY]  [Hysteria2]    [SS2022]
         Port 443         Port 8443      Port 9443
         TCP              UDP/QUIC       TCP
         (основной)       (быстрый)      (запасной)
```

1. **Основной:** VLESS + REALITY (порт 443) -- маскируется под HTTPS
2. **Резервный быстрый:** Hysteria2 -- максимальная скорость
3. **Запасной:** Shadowsocks 2022 -- если первые два заблокированы

### Дополнительные меры:

1. **BBR** -- обязательно включить для ускорения TCP
2. **Cloudflare CDN** -- можно завернуть VLESS через WebSocket через CF (скрывает IP сервера)
3. **IPv6** -- если провайдер блокирует IPv4, использовать IPv6
4. **Несколько VPS** -- в разных странах (Нидерланды, Германия, Финляндия)
5. **Менять dest/SNI** -- если один SNI заблокируют, поменять на другой популярный сайт

### Выбор dest/SNI для REALITY:

Сайт для маскировки должен:
- Поддерживать TLSv1.3 и HTTP/2
- Быть популярным (не вызывать подозрений)
- Не редиректить на другой домен
- Быть доступным из страны блокировки

**Хорошие варианты:**
- `www.microsoft.com`
- `www.samsung.com`
- `www.googletagmanager.com`
- `cdn.shopify.com`
- `www.lovelive-anime.jp` (часто используется в Китае)
- `dl.google.com`

---

---

## Маскировка трафика: как сделать правильно (обновлено 09.02.2026)

### Почему НЕ надо маскироваться под Яндекс/VK напрямую

Интуитивно кажется логичным: "замаскирую трафик под Яндекс -- провайдер не заблокирует". Но это **неправильный подход**:

1. **REALITY использует SNI реального сайта.** Если ваш VPS стоит в Германии, а SNI указан как `yandex.ru`, DPI увидит аномалию: зачем трафик к yandex.ru идет на немецкий IP? Яндекс не хостится в Германии.

2. **Правило REALITY:** dest/SNI должен быть сайтом, который **реально хостится рядом с вашим VPS** (в том же дата-центре или хотя бы в той же стране). Иначе маскировка неубедительна.

3. **Яндекс и VK -- российские сайты.** Если ваш VPS за границей, маскировка под них -- красный флаг для ТСПУ.

### Правильные стратегии маскировки

#### Стратегия 1: REALITY с правильным SNI (простая)

Для VPS в Европе используйте **иностранные** популярные сайты:

```
VPS в Германии → dest: www.microsoft.com:443 (или сайт из той же подсети)
VPS в Нидерландах → dest: www.samsung.com:443
VPS в Финляндии → dest: dl.google.com:443
```

**Как найти идеальный SNI для вашего VPS:**

Используйте `RealiTLScanner` -- он сканирует подсеть вашего VPS и находит сайты с TLSv1.3 + H2:

```bash
# На VPS:
wget https://github.com/XTLS/RealiTLScanner/releases/latest/download/RealiTLScanner-linux-64
chmod +x RealiTLScanner-linux-64

# Сканируем подсеть (замените на IP вашего VPS)
./RealiTLScanner-linux-64 -addr YOUR_VPS_IP/24
```

Скрипт выдаст список доменов в вашей подсети, которые подходят для dest/SNI. Это самая убедительная маскировка -- трафик идет к IP из того же диапазона.

Также есть инструмент **Reality-SNI-Finder** (github.com/meower1/Reality-SNI-finder) -- автоматически ранжирует домены по TLS ping.

#### Стратегия 2: Цепочка через российский VPS (самая надежная для РФ)

Это **самый устойчивый** метод для обхода ТСПУ в 2025-2026. Суть:

```
[Ваш компьютер] → [VPS в России] → [VPS за границей] → [Интернет]
      ^                ^                  ^
  Клиент         "Прокладка"          "Ворота"
                (Yandex Cloud)        (Европа)
```

**Почему это работает:**
- ТСПУ фильтрует **международный** трафик гораздо жестче, чем **внутрироссийский**
- Трафик от вашего компьютера до VPS в Яндекс.Облаке выглядит как обычный запрос к российскому серверу
- Трафик от российского VPS до зарубежного -- это трафик между серверами, он фильтруется слабее
- Даже если ТСПУ "замораживает" прямые подключения за рубеж после 15-20 КБ, внутрироссийский трафик проходит свободно

**Как настроить:**

**Шаг 1: Зарубежный VPS ("Gate" / "Ворота")**

Любой VPS в Европе (Нидерланды, Германия, Финляндия). Настройка:
- Установить 3X-UI или Xray вручную
- Создать VLESS + REALITY inbound
- Найти dest/SNI через RealiTLScanner

**Шаг 2: Российский VPS ("Middleman" / "Прокладка")**

Дешевый VPS в **Яндекс.Облаке**, VK Cloud или EDGE:
- Яндекс.Облако -- самый надежный (IP-диапазоны Яндекса не блокируются)
- VK Cloud -- бесплатный трафик, но сложнее найти "белые" IP
- Стоимость: от 300-500 руб/мес

Конфигурация Xray на российском VPS:

```json
{
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "ВАШ-UUID",
            "flow": ""
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "xhttp",
        "xhttpSettings": {
          "mode": "packet-up"
        },
        "security": "reality",
        "realitySettings": {
          "dest": "yandex.ru:443",
          "serverNames": ["yandex.ru"],
          "privateKey": "ВАШ-КЛЮЧ",
          "shortIds": ["ВАШ-SHORT-ID"]
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "tag": "to-gate",
      "settings": {
        "vnext": [
          {
            "address": "IP-ЗАРУБЕЖНОГО-VPS",
            "port": 443,
            "users": [
              {
                "id": "UUID-НА-ЗАРУБЕЖНОМ",
                "flow": "xtls-rprx-vision",
                "encryption": "none"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "SNI-ЗАРУБЕЖНОГО-VPS",
          "publicKey": "ПУБЛИЧНЫЙ-КЛЮЧ-ЗАРУБЕЖНОГО",
          "shortId": "SHORT-ID-ЗАРУБЕЖНОГО",
          "fingerprint": "chrome"
        }
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "inboundTag": ["inbound-0"],
        "outboundTag": "to-gate"
      }
    ]
  }
}
```

**И вот здесь** маскировка под yandex.ru в SNI **правильна** -- потому что VPS стоит в Яндекс.Облаке, и трафик к yandex.ru на IP Яндекса выглядит абсолютно нормально.

**Шаг 3: Клиент (ваш компьютер)**

В Hiddify Next / v2rayN указываете подключение к **российскому VPS** (не к зарубежному!):
- Адрес: IP российского VPS
- Порт: 443
- Protocol: VLESS
- Security: Reality
- SNI: yandex.ru
- Flow: (пусто, если xhttp)

#### Стратегия 3: VLESS + WebSocket + CDN (Cloudflare)

Ещё один мощный вариант -- завернуть трафик через Cloudflare CDN:

```
[Клиент] → [Cloudflare CDN] → [Ваш VPS] → [Интернет]
```

**Плюсы:**
- IP вашего VPS полностью скрыт за Cloudflare
- Трафик идет к IP Cloudflare, которые используются миллионами сайтов
- Даже если заблокируют ваш IP -- CDN не заблокируют (это сломает весь интернет)

**Минусы:**
- Нужен свой домен (можно бесплатный на freenom или через Cloudflare Registrar)
- Чуть медленнее из-за CDN-прослойки
- Reality не работает через CDN (используется WebSocket + TLS)

### Итоговая рекомендация по маскировке

| Ситуация | Рекомендация |
|---|---|
| VPS за границей, блокировки умеренные | VLESS + REALITY + правильный SNI (RealiTLScanner) |
| VPS за границей, блокировки жесткие (ТСПУ шейпит) | Цепочка: РФ VPS (Яндекс) → зарубежный VPS |
| Нужна максимальная скрытность IP | VLESS + WebSocket + Cloudflare CDN |
| Нужен backup на случай блокировки | Несколько протоколов: REALITY + Hysteria2 + SS2022 |

---

## OPSEC: как не светить себя (обновлено 09.02.2026)

### Проблема с Яндекс.Облаком и подобными

Яндекс Cloud, VK Cloud, любой российский хостер:
- **KYC обязателен** -- паспорт, телефон, часто юрлицо
- Логи хранятся и выдаются по запросу (закон РФ, СОРМ)
- Ваш IP при регистрации и управлении -- записан
- По сути, использовать РФ-хостер для privacy -- противоречие

### Правильная цепочка: анонимные VPS без KYC

#### Шаг 1: Анонимные VPS-провайдеры (оплата крипто, без паспорта)

| Провайдер | Цена | Оплата | KYC | Локации | Примечания |
|---|---|---|---|---|---|
| **AnonVM** | от $5.39/мес | 150+ криптовалют | Нет | Offshore | LUKS-шифрование дисков, DMCA ignore |
| **SporeStack** | от $8/мес | Monero, BTC, BCH | Нет, даже email не нужен | EU, US | API-driven, максимальная анонимность |
| **Hiddence** | от EUR 18/мес | Monero, BTC, altcoins | Нет | Белиз | NVMe, DDR5, TOR Client Area |
| **BitLaunch** | от $10/мес | BTC, LTC, ETH | Нет (только email) | EU, US | Почасовая оплата, быстрый деплой |
| **HostEONS** | от $3/мес | BTC, XMR, ETH, USDT | Нет | US, Германия, Франция | Бюджетный, хорошие локации |
| **LunarVPS** | от $5/мес | BTC, XMR, LTC, USDT | Нет | Нидерланды, Швейцария | Privacy-юрисдикции |
| **ClientVPS** | от $15/мес | BTC, XMR, Dash | Нет | EU | Dash для полной untraceable оплаты |
| **QloudHost** | от $18/мес | BTC, ETH | Нет (только email) | Нидерланды | DMCA ignore, no-log policy |
| **SurferCloud** | от $6.75/мес | BTC, USDT, ETH | Нет | EU, US | Free trial, почасовая оплата |

**Лучший выбор для максимальной анонимности:** SporeStack (даже email не нужен) или Hiddence (Monero + TOR-панель).

**Лучший выбор по балансу цена/качество:** HostEONS (от $3/мес, Германия/Франция) или BitLaunch.

#### Шаг 2: Как платить анонимно

**Monero (XMR) -- золотой стандарт приватных платежей:**
- Транзакции **по умолчанию приватные** (в отличие от Bitcoin, где все видно в блокчейне)
- Отправителя, получателя и сумму невозможно отследить
- Купить XMR можно P2P без KYC (LocalMonero-аналоги, Bisq, Haveno)

**Bitcoin (BTC) -- приемлемо, но с оговорками:**
- Все транзакции публичны в блокчейне
- Если купить BTC на KYC-бирже → привязка к личности
- Решение: купить BTC P2P за наличные, или обменять через CoinJoin/миксер

**Порядок действий:**
1. Купить Monero P2P (без верификации)
2. Оплатить VPS через Monero
3. Никакой связи между вашей личностью и сервером

#### Шаг 3: Как не светить свой IP при настройке VPS

**Проблема:** Даже если VPS анонимный, при SSH-подключении к нему ваш реальный IP записывается в логи сервера и может быть виден хостеру.

**Решения:**

**A) Подключаться через Tor:**
```bash
# Установить tor
sudo apt install tor

# SSH через Tor
torify ssh root@your-vps-ip

# Или через torsocks
torsocks ssh root@your-vps-ip
```

**B) Подключаться через публичный WiFi:**
- Кафе, библиотека, коворкинг
- MAC-адрес рандомизировать заранее
- Не подключаться к WiFi, где есть камеры + ваш паспорт (например отель)

**C) Подключаться через другой VPN/прокси:**
- Любой VPN → SSH к вашему VPS
- Ваш реальный IP не виден серверу

**D) Использовать .onion-панель управления:**
- Hiddence предоставляет TOR Client Area
- Управление VPS полностью через Tor -- IP не засвечен вообще

#### Шаг 4: Полная анонимная архитектура

Если цепочка через РФ VPS нужна, но без KYC:

```
Вариант А: Без российского VPS (проще)

[Вы] → Tor/VPN → [Анонимный VPS в Европе] → [Интернет]
                   (оплата Monero, без KYC)
                   VLESS + REALITY
                   SNI = сайт из той же подсети
```

```
Вариант Б: Цепочка из двух анонимных VPS

[Вы] → [Анонимный VPS #1 в Европе] → [Анонимный VPS #2 в другой стране] → [Интернет]
        (entry node, ближе к вам)        (exit node)
        VLESS + REALITY                   VLESS + REALITY
```

```
Вариант В: С CDN-прослойкой (скрывает оба IP)

[Вы] → [Cloudflare CDN] → [Анонимный VPS] → [Интернет]
        IP CF невозможно           IP VPS скрыт
        заблокировать              за Cloudflare
```

#### Шаг 5: Checklist полной анонимности

- [ ] VPS оплачен Monero (не BTC с KYC-биржи)
- [ ] При регистрации использован одноразовый email (guerrillamail, protonmail)
- [ ] SSH-подключение только через Tor/VPN/публичный WiFi
- [ ] На VPS нет ваших реальных данных (имя, email, ключи с вашего основного компьютера)
- [ ] DNS-запросы идут через VPN (не утекают к провайдеру)
- [ ] WebRTC отключен в браузере (не утекает реальный IP)
- [ ] Таймзона и язык в браузере не выдают вашу локацию

### Что использовать вместо Яндекс.Облака для "прокладки"

Если нужна именно цепочка (entry-node в стране с мягкой фильтрацией), есть варианты:

1. **Анонимный VPS в Турции/Сербии/Казахстане** -- нейтральные страны, трафик в Европу не фильтруется
2. **Анонимный VPS в Финляндии** -- географически близко к РФ, хорошие пинги
3. **Два VPS в Европе** (напр. Финляндия + Нидерланды) -- мультихоп без РФ-ноды вообще

По сути, если ТСПУ не шейпит ваш трафик до конкретного европейского IP (а обычно шейпит только прямые подключения к "подозрительным" IP), достаточно **одного анонимного VPS в Европе** с правильно настроенным REALITY.

Цепочка через РФ нужна только если:
- Прямые подключения за рубеж режутся после 15-20 КБ
- IP вашего VPS попал в блоклист
- Провайдер блокирует весь TLS-трафик к иностранным IP на 443 порту

---

## Источники

1. [HeisenGuard - VPN Protocols 2026](https://heisenguard.com/the-definitive-guide-to-vpn-protocols-in-2026-speed-security-and-anti-censorship/)
2. [OctoHide - VLESS vs Xray vs Reality](https://octohide.com/support/blog/What-s-the-Difference-Between-VLESS-Xray-Reality-and-VMess)
3. [XTLS/REALITY GitHub](https://github.com/XTLS/REALITY/blob/main/README.en.md)
4. [DeepWiki - REALITY Protocol](https://deepwiki.com/XTLS/Xray-core/4.2-reality-protocol)
5. [Hostry - Evolution of Censorship Tools](https://hostry.com/blog/evolution-of-internet-censorship-circumvention-tools-shadowsocks-v2ray-xray-and-their-protocols-vmess-vless-xtls/)
6. [XHTTP+Reality Xray-VLESS 2025](https://kejilaowang.com/en/xhttprealitys-xray-vless-protocol-as-the-newest-and-most-secure-encryption-for-scientific-internet-access-in-2025/)
7. [3X-UI GitHub](https://github.com/MHSanaei/3x-ui)
8. [Hysteria2 Official](https://v2.hysteria.network/)
9. [sing-box Documentation](https://sing-box.sagernet.org/)
10. [TechRadar - Future of VPN Protocols](https://www.techradar.com/vpn/vpn-privacy-security/forget-openvpn-wireguard-this-is-the-vpn-protocol-of-the-future)
11. [XTLS Iran Reality Setup](https://github.com/SasukeFreestyle/XTLS-Iran-Reality)
12. [Coexisting Vision + XHTTP Reality](https://henrywithu.com/coexisting-xray-vless-tcp-xtls-vision-and-vless-xhttp-reality-on-a-single-port/)
13. [Habr - VLESS+Reality Multi-hop архитектура цепочки](https://habr.com/ru/articles/926786)
14. [Habr - Гайд по обходу белых списков и цепочки](https://habr.com/ru/articles/985674/)
15. [Habr - XTLS-Reality маскировка HAProxy steal-oneself](https://habr.com/ru/articles/885276)
16. [Habr - FAQ Shadowsocks/XRay/XTLS/Reality обход блокировок](https://habr.com/ru/articles/770400/)
17. [Habr - VLESS обход цензуры в России 2025](https://habr.com/ru/articles/963022/)
18. [RealiTLScanner GitHub](https://github.com/XTLS/RealiTLScanner)
19. [Reality-SNI-Finder GitHub](https://github.com/meower1/Reality-SNI-finder)
20. [Xray-core Dest & SNI Discussion](https://github.com/XTLS/Xray-core/discussions/2431)
