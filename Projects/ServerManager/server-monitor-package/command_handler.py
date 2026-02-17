#!/usr/bin/env python3
"""
=============================================================================
COMMAND HANDLER - Обработчик команд от Google Sheets
=============================================================================
Описание: Flask webhook для приёма и выполнения команд на Windows серверах
Версия: 3.1 (с поддержкой set_proxy)
Дата: 21.01.2026
=============================================================================
"""

from flask import Flask, request, jsonify
import logging
import requests
from datetime import datetime
import time

from winrm_connector import WinRMConnector
from server_checker import ServerChecker
import config

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ FLASK ПРИЛОЖЕНИЯ
# =============================================================================

app = Flask(__name__)

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ
# =============================================================================

connector = WinRMConnector(timeout=config.WINRM_TIMEOUT)
checker = ServerChecker()

# =============================================================================
# ФУНКЦИЯ: Парсинг реквизитов прокси
# =============================================================================

def parse_proxy_credentials(proxy_string):
    if not proxy_string or not proxy_string.strip():
        return None

    proxy_string = proxy_string.strip()
    result = {
        'protocol': 'SOCKS5',
        'address': '',
        'port': 0,
        'username': '',
        'password': ''
    }

    try:
        if '://' in proxy_string:
            protocol_part, rest = proxy_string.split('://', 1)
            result['protocol'] = protocol_part.upper()

            if '@' in rest:
                auth_part, host_part = rest.split('@', 1)
                if ':' in auth_part:
                    result['username'], result['password'] = auth_part.split(':', 1)
                else:
                    result['username'] = auth_part

                if ':' in host_part:
                    result['address'], port_str = host_part.rsplit(':', 1)
                    result['port'] = int(port_str)
                else:
                    return None
            else:
                if ':' in rest:
                    result['address'], port_str = rest.rsplit(':', 1)
                    result['port'] = int(port_str)
                else:
                    return None
        else:
            parts = proxy_string.split(':')

            if len(parts) == 2:
                result['address'] = parts[0]
                result['port'] = int(parts[1])
            elif len(parts) == 4:
                result['address'] = parts[0]
                result['port'] = int(parts[1])
                result['username'] = parts[2]
                result['password'] = parts[3]
            else:
                return None

        valid_protocols = ['SOCKS5', 'SOCKS4', 'HTTP', 'HTTPS']
        if result['protocol'] not in valid_protocols:
            result['protocol'] = 'SOCKS5'

        if not (1 <= result['port'] <= 65535):
            return None

        if not result['address']:
            return None

        return result

    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing proxy credentials: {e}")
        return None

# =============================================================================
# ФУНКЦИЯ: Выполнение команды на сервере
# =============================================================================

def execute_command(rdp, command, proxy_key=None, proxyma_api_key=None, proxy_credentials=None):
    try:
        parts = rdp.split(':')
        if len(parts) < 3:
            return "❌ Ошибка: Неверный формат RDP", {}

        ip = parts[0].strip()
        username = parts[1].strip()
        password = ':'.join(parts[2:]).strip()

        start_time = datetime.now()

        # =========================================================================
        # КОМАНДА: check
        # =========================================================================
        if command == 'check':
            check_result = checker.check_full_status(ip, username, password)

            if check_result['success']:
                result_text = f"✅ Проверка завершена ({start_time.strftime('%H:%M:%S')})\n"
                result_text += f"IP: {check_result['currentIp']}\n"
                result_text += f"Город: {check_result['currentCity']}\n"
                result_text += f"Proxifier: {'✅' if check_result['statusProxy'] == 'OK' else '❌'}\n"
                result_text += f"AnyDesk: {'✅' if check_result['anydesk'] else '❌'}\n"
                result_text += f"RustDesk: {'✅' if check_result['rustdesk'] else '❌'}"
                return result_text, check_result
            else:
                result_text = f"❌ Не удалось подключиться к серверу ({start_time.strftime('%H:%M:%S')})"
                return result_text, check_result

        # =========================================================================
        # КОМАНДА: check_proxyma
        # =========================================================================
        elif command == 'check_proxyma':
            if not proxyma_api_key:
                return "❌ Proxyma API Key не указан в таблице", {}
            if not proxy_key:
                return "❌ Package Key не указан в таблице", {}

            from proxyma_api import ProxymaAPI
            proxyma = ProxymaAPI(proxyma_api_key)

            info = proxyma.get_package_info(proxy_key)
            if not info:
                return "❌ Не удалось получить данные пакета", {}

            packages = proxyma.get_packages()
            pkg_name = "Unknown"
            for pkg in packages:
                if pkg['package_key'] == proxy_key:
                    pkg_name = pkg['title']
                    break

            balance = proxyma.get_balance()
            tariff_price = proxyma.get_tariff_price(pkg_name)

            try:
                expire_date = datetime.strptime(info['expired_at'], '%Y-%m-%d')
                days_left = (expire_date - datetime.now()).days
            except:
                days_left = "N/A"

            result_text = f"✅ Proxyma ({start_time.strftime('%H:%M:%S')})\n"
            result_text += f"Пакет: {pkg_name}\n"
            result_text += f"Трафик: {info['traffic']['usage']:.2f} / {info['traffic']['limit']} GB\n"
            result_text += f"Осталось: {info['traffic']['limit'] - info['traffic']['usage']:.2f} GB\n"
            result_text += f"Истекает: {info['expired_at']} ({days_left} дней)\n"
            result_text += f"Баланс: ${balance}\n"
            result_text += f"Цена тарифа: {tariff_price}"

            proxy_data = {
                'proxyName': pkg_name,
                'proxyLimit': info['traffic']['limit'],
                'proxyUsed': round(info['traffic']['usage'], 2),
                'proxyLeft': round(info['traffic']['limit'] - info['traffic']['usage'], 2),
                'proxyExpires': info['expired_at'],
                'proxyCheckTime': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'proxyBalance': balance if balance else 'N/A',
                'proxyPrice': tariff_price if tariff_price else 'N/A'
            }

            return result_text, proxy_data

        # =========================================================================
        # КОМАНДА: get_timezone
        # =========================================================================
        elif command == 'get_timezone':
            tz_info = checker.get_timezone(ip, username, password)
            if tz_info:
                result_text = f"✅ Таймзона ({start_time.strftime('%H:%M:%S')})\n"
                result_text += f"ID: {tz_info['id']}\n"
                result_text += f"Название: {tz_info['displayName']}\n"
                result_text += f"Смещение: {tz_info['offset']}\n"
                result_text += f"Время на сервере: {tz_info['currentTime']}"
                return result_text, {}
            else:
                return f"❌ Не удалось получить таймзону ({start_time.strftime('%H:%M:%S')})", {}

        # =========================================================================
        # КОМАНДА: set_timezone_msk
        # =========================================================================
        elif command == 'set_timezone_msk':
            ps_cmd = '''Set-TimeZone -Id "Russian Standard Time"'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(2)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ Таймзона изменена на Moscow (MSK) ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: set_timezone_ekt
        # =========================================================================
        elif command == 'set_timezone_ekt':
            ps_cmd = '''Set-TimeZone -Id "Ekaterinburg Standard Time"'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(2)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ Таймзона изменена на Ekaterinburg/Perm (EKT) ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: get_languages
        # =========================================================================
        elif command == 'get_languages':
            langs = checker.get_languages(ip, username, password)
            if langs:
                result_text = f"✅ Установленные языки ({start_time.strftime('%H:%M:%S')})\n"
                result_text += '\n'.join([f"- {lang}" for lang in langs if lang.strip()])
                return result_text, {}
            else:
                return f"❌ Не удалось получить список языков ({start_time.strftime('%H:%M:%S')})", {}

        # =========================================================================
        # КОМАНДА: set_lang_russian
        # =========================================================================
        elif command == 'set_lang_russian':
            ps_cmd = '''Set-WinUILanguageOverride -Language ru-RU; Set-Culture -CultureInfo ru-RU'''
            connector.execute_command(ip, username, password, ps_cmd)
            return f"✅ Язык изменен на русский (требуется перезагрузка) ({start_time.strftime('%H:%M:%S')})", {}

        # =========================================================================
        # КОМАНДА: set_lang_english
        # =========================================================================
        elif command == 'set_lang_english':
            ps_cmd = '''Set-WinUILanguageOverride -Language en-US; Set-Culture -CultureInfo en-US'''
            connector.execute_command(ip, username, password, ps_cmd)
            return f"✅ Язык изменен на английский (требуется перезагрузка) ({start_time.strftime('%H:%M:%S')})", {}

        # =========================================================================
        # КОМАНДА: start_proxifier
        # =========================================================================
        elif command == 'start_proxifier':
            app_path = checker.find_app_path(ip, username, password, "Proxifier")
            if not app_path:
                app_path = "C:\\Program Files (x86)\\Proxifier\\Proxifier.exe"

            ps_cmd = f'''Start-Process "{app_path}"'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(5)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ Proxifier запущен ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: stop_proxifier
        # =========================================================================
        elif command == 'stop_proxifier':
            ps_cmd = '''Stop-Process -Name Proxifier -Force -EA 0'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(3)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ Proxifier остановлен ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: restart_proxifier
        # =========================================================================
        elif command == 'restart_proxifier':
            app_path = checker.find_app_path(ip, username, password, "Proxifier")
            if not app_path:
                app_path = "C:\\Program Files (x86)\\Proxifier\\Proxifier.exe"

            ps_cmd = f'''Stop-Process -Name Proxifier -Force -EA 0; Start-Sleep 3; Start-Process "{app_path}"'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(6)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ Proxifier перезапущен ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: set_proxy - Изменение настроек прокси в Proxifier
        # =========================================================================
        elif command == 'set_proxy':
            if not proxy_credentials:
                return "❌ Реквизиты прокси не указаны в таблице", {}

            parsed = parse_proxy_credentials(proxy_credentials)
            if not parsed:
                return "❌ Неверный формат реквизитов прокси. Используйте: IP:PORT или IP:PORT:LOGIN:PASSWORD", {}

            protocol = parsed['protocol']
            address = parsed['address']
            port = parsed['port']
            proxy_user = parsed.get('username', '')
            proxy_pass = parsed.get('password', '')

            # Компактный PowerShell скрипт (строковая замена, перезапуск если запущен)
            ps_cmd = f'''$p="{protocol}";$a="{address}";$pt={port};$u="{proxy_user}";$pw="{proxy_pass}";$pp="$env:APPDATA\\Proxifier4\\Profiles\\Default.ppx";if(!(Test-Path $pp)){{$pp="$env:ProgramData\\Proxifier\\Default.ppx"}};if(!(Test-Path $pp)){{echo "ERR:NoProfile";exit 1}};cp $pp "$pp.bak" -Force;$c=[IO.File]::ReadAllText($pp);if($u -and $pw){{$n='<ProxyList><Proxy id="100" type="'+$p+'"><Address>'+$a+'</Address><Port>'+$pt+'</Port><Options>0</Options><Authentication enabled="true"><Username>'+$u+'</Username><Password>'+$pw+'</Password></Authentication></Proxy></ProxyList>'}}else{{$n='<ProxyList><Proxy id="100" type="'+$p+'"><Address>'+$a+'</Address><Port>'+$pt+'</Port><Options>0</Options></Proxy></ProxyList>'}};if($c -match '<ProxyList\\s*/>'){{$c=$c -replace '<ProxyList\\s*/>',$n}}elseif($c -match '<ProxyList>.*?</ProxyList>'){{$c=$c -replace '<ProxyList>.*?</ProxyList>',$n}};$enc=New-Object System.Text.UTF8Encoding $false;[IO.File]::WriteAllText($pp,$c,$enc);$running=Get-Process Proxifier -EA 0;if($running){{Stop-Process -Name Proxifier -Force;sleep 2;$px="C:\\Program Files (x86)\\Proxifier\\Proxifier.exe";if(!(Test-Path $px)){{$px="C:\\Program Files\\Proxifier\\Proxifier.exe"}};$tn="StartPx";schtasks /Delete /TN $tn /F 2>$null;schtasks /Create /TN $tn /TR "`"$px`"" /SC ONCE /ST 00:00 /RU SYSTEM /F 2>$null;schtasks /Run /TN $tn 2>$null;sleep 2;schtasks /Delete /TN $tn /F 2>$null;echo "OK:$p`://$a`:$pt (restarted)"}}else{{echo "OK:$p`://$a`:$pt (profile updated, start Proxifier manually)"}}'''

            output = connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(3)
            check_result = checker.check_full_status(ip, username, password)

            if output and "OK:" in output:
                return f"✅ Прокси обновлен ({start_time.strftime('%H:%M:%S')}): {protocol}://{address}:{port}", check_result
            elif output and "ERR:NoProfile" in output:
                return f"❌ Профиль Proxifier не найден ({start_time.strftime('%H:%M:%S')})", check_result
            else:
                return f"❌ Ошибка ({start_time.strftime('%H:%M:%S')}): {output if output else 'Нет ответа'}", check_result

        # =========================================================================
        # КОМАНДА: start_anydesk
        # =========================================================================
        elif command == 'start_anydesk':
            app_path = checker.find_app_path(ip, username, password, "AnyDesk")
            if not app_path:
                app_path = "C:\\Program Files (x86)\\AnyDesk\\AnyDesk.exe"

            ps_cmd = f'''Start-Process "{app_path}"'''
            connector.execute_command(ip, username, password, ps_cmd)
            time.sleep(3)
            check_result = checker.check_full_status(ip, username, password)
            return f"✅ AnyDesk запущен ({start_time.strftime('%H:%M:%S')})", check_result

        # =========================================================================
        # КОМАНДА: create_shortcuts
        # =========================================================================
        elif command == 'create_shortcuts':
            ps_cmd = '''
New-Item -Path "C:\\ServerApps" -ItemType Directory -Force | Out-Null
$results = @()
$ProxifierPaths = @("C:\\Program Files (x86)\\Proxifier\\Proxifier.exe","C:\\Program Files\\Proxifier\\Proxifier.exe","C:\\Proxifier\\Proxifier.exe")
$ProxifierFound = $false
foreach ($path in $ProxifierPaths) {
    if (Test-Path $path) {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("C:\\ServerApps\\Proxifier.lnk")
        $Shortcut.TargetPath = $path
        $Shortcut.Save()
        $results += "Proxifier: $path"
        $ProxifierFound = $true
        break
    }
}
if (-not $ProxifierFound) { $results += "Proxifier не найден" }
$AnyDeskPaths = @("C:\\Program Files (x86)\\AnyDesk\\AnyDesk.exe","C:\\Program Files\\AnyDesk\\AnyDesk.exe","C:\\AnyDesk\\AnyDesk.exe")
$AnyDeskFound = $false
foreach ($path in $AnyDeskPaths) {
    if (Test-Path $path) {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("C:\\ServerApps\\AnyDesk.lnk")
        $Shortcut.TargetPath = $path
        $Shortcut.Save()
        $results += "AnyDesk: $path"
        $AnyDeskFound = $true
        break
    }
}
if (-not $AnyDeskFound) { $results += "AnyDesk не найден" }
$results -join "`n"
'''
            output = connector.execute_command(ip, username, password, ps_cmd)
            return f"✅ Создание ярлыков завершено ({start_time.strftime('%H:%M:%S')})\n{output}", {}

        # =========================================================================
        # КОМАНДА: reboot
        # =========================================================================
        elif command == 'reboot':
            ps_cmd = '''Restart-Computer -Force'''
            connector.execute_command(ip, username, password, ps_cmd)
            return f"✅ Перезагрузка запущена ({start_time.strftime('%H:%M:%S')})\nСервер будет недоступен 2-3 минуты", {}

        # =========================================================================
        # НЕИЗВЕСТНАЯ КОМАНДА
        # =========================================================================
        else:
            return f"❌ Неизвестная команда: {command}", {}

    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return f"❌ Ошибка выполнения: {str(e)}", {}

# =============================================================================
# ENDPOINT: /execute_command
# =============================================================================

@app.route('/execute_command', methods=['POST'])
def handle_command():
    try:
        data = request.get_json()
        rdp = data.get('rdp')
        command = data.get('command')
        proxy_key = data.get('proxyKey')
        proxyma_api_key = data.get('proxymaApiKey')
        proxy_credentials = data.get('proxyCredentials')

        logger.info(f"Executing '{command}' on {rdp}")

        result_text, server_status = execute_command(rdp, command, proxy_key, proxyma_api_key, proxy_credentials)

        update_data = {
            'rdp': rdp,
            'clearCommand': True,
            'datetime': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }

        if command == 'check':
            update_data['checkServerResult'] = result_text
        elif command == 'check_proxyma':
            update_data['checkProxyResult'] = result_text
        else:
            update_data['commandResult'] = result_text

        if server_status:
            update_data.update(server_status)

        requests.post(config.SHEETS_API_URL, json=update_data,
                     headers={'Content-Type': 'application/json'},
                     timeout=config.API_TIMEOUT)

        return jsonify({'success': True, 'result': result_text})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# =============================================================================
# ENDPOINT: /health
# =============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
