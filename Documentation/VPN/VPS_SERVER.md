# VPN Server (VPS)

**Провайдер:** KVM-2
**Назначение:** VPN

## Доступы

| Параметр | Значение |
|---|---|
| **IP** | `169.40.135.130` |
| **Root pass** | `Taurus!2025` |
| **OS** | Ubuntu 24.04 LTS |
| **ServerName** | VPN |

## SSH подключение

```powershell
ssh root@169.40.135.130
# Или через скрипт:
python Scripts/vps_cmd.py "command"
```

## 3X-UI Panel

| Параметр | Значение |
|---|---|
| **URL** | `https://169.40.135.130:2053/` |
| **Username** | `admin` |
| **Password** | `admin` |
| **Port** | `2053` |
| **Version** | `v2.8.9` |
| **SSL** | Let's Encrypt (auto-renew) |

**ВАЖНО:** Смени пароль панели при первом входе!

## VLESS + REALITY (основной)

| Параметр | Значение |
|---|---|
| **Port** | `443` |
| **Protocol** | VLESS |
| **Security** | Reality |
| **Flow** | `xtls-rprx-vision` |
| **UUID** | `00a2711a-0e0d-41a5-b446-da70f3e7a3e7` |
| **Public Key** | `V2mkZpZoj5Yoh0VZZFTYvjWsnRqCJPJUMpl7av9myUg` |
| **Private Key** | `OAN9pDobMxSaI0gvgslBP0qNgsBMWtCDK7Ac9w5HwHI` |
| **Short ID** | `993b61a18284803a` |
| **SNI / Dest** | `www.cloudflare.com` (из той же подсети /24) |
| **Fingerprint** | `chrome` |

### Ссылка для подключения (вставить в Hiddify/v2rayN):

```
vless://00a2711a-0e0d-41a5-b446-da70f3e7a3e7@169.40.135.130:443?type=tcp&security=reality&pbk=V2mkZpZoj5Yoh0VZZFTYvjWsnRqCJPJUMpl7av9myUg&fp=chrome&sni=www.cloudflare.com&sid=993b61a18284803a&flow=xtls-rprx-vision#VLESS-Reality
```

## RealiTLScanner: найденные SNI в подсети

```
169.40.135.6   tender-grothendieck.169-40-135-6.plesk.page  TLS1.3 h2
169.40.135.20  cache.trendlabs.pro                          TLS1.3 h2
169.40.135.46  shrt.tips                                    TLS1.3 h2
169.40.135.60  ordexiamarket.com                            TLS1.3 h2
169.40.135.78  deticket.online                              TLS1.3 h2
169.40.135.91  www.cloudflare.com         <-- ИСПОЛЬЗУЕТСЯ  TLS1.3 h2
169.40.135.160 beautiful-hellman.169-40-135-160.plesk.page  TLS1.3 h2
169.40.135.189 coinstash.slgnup.com                         TLS1.3 h2
169.40.135.225 cloudflare-dns.com                           TLS1.3 h2
```

## Статус настройки

- [x] Система обновлена (apt update && upgrade)
- [x] BBR включен (fq + bbr)
- [x] 3X-UI установлен (v2.8.9, SSL, порт 2053)
- [x] RealiTLScanner -- найден SNI (www.cloudflare.com, та же подсеть)
- [x] VLESS + REALITY настроен (порт 443)
- [ ] Hysteria2 настроен (добавить через веб-панель)
- [ ] Клиент Hiddify установлен на ПК
- [ ] Проверка работы (whatismyip)
- [ ] Сменить пароль панели 3X-UI

## Заметки

- Инструкция: `Documentation/VPN/VPN_PROTOCOLS_RESEARCH_2026.md`
- SSH скрипт: `Scripts/vps_cmd.py "command"`
- Сертификат для Hysteria2 уже создан: `/etc/hysteria/cert.pem` + `/etc/hysteria/private.key`
