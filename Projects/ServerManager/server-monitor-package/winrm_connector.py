#!/usr/bin/env python3
"""
=============================================================================
WINRM CONNECTOR - Модуль для выполнения команд через WinRM
=============================================================================
Описание:
- Подключается к Windows серверам через WinRM (порт 5985)
- Выполняет PowerShell команды удалённо
- Использует NTLM аутентификацию
- Работает через SOAP протокол
Версия: 3.1
Дата: 26.01.2026
Изменения: Добавлен фильтр для HeaderParsingError от urllib3
=============================================================================
"""

import logging
import warnings
import requests
from requests_ntlm import HttpNtlmAuth
import xml.etree.ElementTree as ET
import uuid
import time
import base64

# Подавляем предупреждения urllib3 о некорректных заголовках от WinRM серверов
# Это известная проблема некоторых WinRM реализаций, не влияет на функциональность
# HeaderParsingError - это Exception, поэтому используем уровень логирования
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

# Также отключаем warnings от urllib3
warnings.filterwarnings('ignore', module='urllib3')

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# КЛАСС: WinRMConnector - Подключение к Windows через WinRM
# =============================================================================
class WinRMConnector:
    """
    Класс для выполнения PowerShell команд на удалённых Windows серверах

    Использует WinRM (Windows Remote Management) протокол для:
    - Создания удалённой оболочки (shell)
    - Выполнения PowerShell команд
    - Получения результатов выполнения

    Аутентификация: NTLM
    Протокол: HTTP (порт 5985)
    Формат: SOAP/XML
    """

    def __init__(self, timeout=30):
        """
        Инициализация WinRM коннектора

        Args:
            timeout (int): Таймаут запросов в секундах (по умолчанию 30)
        """
        self.timeout = timeout

        # XML namespaces для парсинга SOAP ответов
        self.namespaces = {
            's': 'http://www.w3.org/2003/05/soap-envelope',
            'rsp': 'http://schemas.microsoft.com/wbem/wsman/1/windows/shell'
        }

    # =========================================================================
    # МЕТОД: Выполнение PowerShell команды
    # =========================================================================
    def execute_command(self, ip, username, password, ps_command):
        """
        Выполняет PowerShell команду на удалённом Windows сервере

        Процесс выполнения:
        1. Создание WinRM shell (удалённой оболочки)
        2. Запуск PowerShell команды в shell
        3. Получение результата выполнения
        4. Возврат stdout (стандартный вывод)

        Args:
            ip (str): IP адрес Windows сервера
            username (str): Имя пользователя Windows
            password (str): Пароль пользователя
            ps_command (str): PowerShell команда для выполнения

        Returns:
            str or None: Результат выполнения команды или None при ошибке

        Example:
            >>> connector = WinRMConnector()
            >>> result = connector.execute_command(
            ...     '192.168.1.1',
            ...     'Administrator',
            ...     'password',
            ...     'Get-Process | Select-Object -First 5'
            ... )
        """
        try:
            # --- ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ ---
            url = f"http://{ip}:5985/wsman"  # WinRM endpoint
            auth = HttpNtlmAuth(f"{ip}\\{username}", password)  # NTLM auth
            headers = {'Content-Type': 'application/soap+xml;charset=UTF-8'}

            # --- ШАГ 1: СОЗДАНИЕ SHELL ---
            shell_id = self._create_shell(url, auth, headers)
            if not shell_id:
                logger.error(f"Failed to create shell on {ip}")
                return None

            # --- ШАГ 2: ЗАПУСК КОМАНДЫ ---
            command_id = self._run_command(url, auth, headers, shell_id, ps_command)
            if not command_id:
                logger.error(f"Failed to run command on {ip}")
                return None

            # --- ШАГ 3: ПОЛУЧЕНИЕ РЕЗУЛЬТАТА ---
            # _get_output теперь использует polling до завершения команды
            output = self._get_output(url, auth, headers, shell_id, command_id)

            return output

        except Exception as e:
            logger.error(f"WinRM error for {ip}: {e}")
            return None

    # =========================================================================
    # ВНУТРЕННИЙ МЕТОД: Создание WinRM Shell
    # =========================================================================
    def _create_shell(self, url, auth, headers):
        """
        Создаёт удалённую оболочку (shell) на Windows сервере

        Shell - это сессия для выполнения команд. Создаётся один раз,
        затем в нём можно выполнять множество команд.

        Args:
            url (str): WinRM endpoint URL
            auth (HttpNtlmAuth): NTLM аутентификация
            headers (dict): HTTP заголовки

        Returns:
            str or None: Shell ID или None при ошибке
        """
        # Генерация уникального ID сообщения
        msg_id = str(uuid.uuid4())

        # --- ФОРМИРОВАНИЕ SOAP ЗАПРОСА ---
        # Запрос на создание shell с параметрами:
        # - WINRS_NOPROFILE: не загружать профиль пользователя (быстрее)
        # - WINRS_CODEPAGE: 65001 (UTF-8 кодировка)
        create_shell_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd" xmlns:rsp="http://schemas.microsoft.com/wbem/wsman/1/windows/shell">
<s:Header>
<wsa:To>{url}</wsa:To>
<wsa:ReplyTo><wsa:Address s:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>
<wsa:Action s:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2004/09/transfer/Create</wsa:Action>
<wsman:MaxEnvelopeSize s:mustUnderstand="true">512000</wsman:MaxEnvelopeSize>
<wsa:MessageID>uuid:{msg_id}</wsa:MessageID>
<wsman:Locale xml:lang="en-US" s:mustUnderstand="false"/>
<wsman:ResourceURI s:mustUnderstand="true">http://schemas.microsoft.com/wbem/wsman/1/windows/shell/cmd</wsman:ResourceURI>
<wsman:OptionSet>
<wsman:Option Name="WINRS_NOPROFILE">FALSE</wsman:Option>
<wsman:Option Name="WINRS_CODEPAGE">65001</wsman:Option>
</wsman:OptionSet>
<wsman:OperationTimeout>PT60S</wsman:OperationTimeout>
</s:Header>
<s:Body>
<rsp:Shell>
<rsp:InputStreams>stdin</rsp:InputStreams>
<rsp:OutputStreams>stdout stderr</rsp:OutputStreams>
</rsp:Shell>
</s:Body>
</s:Envelope>'''

        # --- ОТПРАВКА ЗАПРОСА ---
        response = requests.post(url, auth=auth, headers=headers, data=create_shell_xml, timeout=self.timeout)

        if response.status_code != 200:
            logger.error(f"Failed to create shell, status: {response.status_code}")
            return None

        # --- ПАРСИНГ ОТВЕТА ---
        # Извлечение Shell ID из XML ответа
        root = ET.fromstring(response.content)
        shell_id_elem = root.find('.//rsp:ShellId', self.namespaces)

        return shell_id_elem.text if shell_id_elem is not None else None

    # =========================================================================
    # ВНУТРЕННИЙ МЕТОД: Запуск команды в Shell
    # =========================================================================
    def _run_command(self, url, auth, headers, shell_id, ps_command):
        """
        Запускает PowerShell команду в существующем shell

        Команда кодируется в Base64 UTF-16LE для безопасной передачи
        специальных символов и многострочных команд.

        Args:
            url (str): WinRM endpoint URL
            auth (HttpNtlmAuth): NTLM аутентификация
            headers (dict): HTTP заголовки
            shell_id (str): ID созданного shell
            ps_command (str): PowerShell команда

        Returns:
            str or None: Command ID или None при ошибке
        """
        # --- КОДИРОВАНИЕ КОМАНДЫ ---
        # PowerShell -EncodedCommand требует Base64 UTF-16LE кодировку
        encoded_cmd = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
        cmd_id = str(uuid.uuid4())

        # --- ФОРМИРОВАНИЕ SOAP ЗАПРОСА ---
        run_cmd_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd" xmlns:rsp="http://schemas.microsoft.com/wbem/wsman/1/windows/shell">
<s:Header>
<wsa:To>{url}</wsa:To>
<wsa:ReplyTo><wsa:Address s:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>
<wsa:Action s:mustUnderstand="true">http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Command</wsa:Action>
<wsman:MaxEnvelopeSize s:mustUnderstand="true">512000</wsman:MaxEnvelopeSize>
<wsa:MessageID>uuid:{cmd_id}</wsa:MessageID>
<wsman:Locale xml:lang="en-US" s:mustUnderstand="false"/>
<wsman:ResourceURI s:mustUnderstand="true">http://schemas.microsoft.com/wbem/wsman/1/windows/shell/cmd</wsman:ResourceURI>
<wsman:SelectorSet>
<wsman:Selector Name="ShellId">{shell_id}</wsman:Selector>
</wsman:SelectorSet>
<wsman:OperationTimeout>PT60S</wsman:OperationTimeout>
</s:Header>
<s:Body>
<rsp:CommandLine>
<rsp:Command>powershell</rsp:Command>
<rsp:Arguments>-NoProfile -EncodedCommand {encoded_cmd}</rsp:Arguments>
</rsp:CommandLine>
</s:Body>
</s:Envelope>'''

        # --- ОТПРАВКА ЗАПРОСА ---
        response = requests.post(url, auth=auth, headers=headers, data=run_cmd_xml, timeout=self.timeout)

        if response.status_code != 200:
            logger.error(f"Failed to run command, status: {response.status_code}")
            return None

        # --- ПАРСИНГ ОТВЕТА ---
        root = ET.fromstring(response.content)
        command_id_elem = root.find('.//rsp:CommandId', self.namespaces)

        return command_id_elem.text if command_id_elem is not None else None

    # =========================================================================
    # ВНУТРЕННИЙ МЕТОД: Получение результата выполнения (с polling)
    # =========================================================================
    def _get_output(self, url, auth, headers, shell_id, command_id):
        """
        Получает результат выполнения команды (stdout) с polling до завершения

        Args:
            url (str): WinRM endpoint URL
            auth (HttpNtlmAuth): NTLM аутентификация
            headers (dict): HTTP заголовки
            shell_id (str): ID shell
            command_id (str): ID команды

        Returns:
            str: Результат выполнения (stdout) или пустая строка
        """
        all_output = []
        max_polls = 20  # Максимум 20 попыток (~60 секунд)

        for poll in range(max_polls):
            # --- ФОРМИРОВАНИЕ SOAP ЗАПРОСА ---
            get_output_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd" xmlns:rsp="http://schemas.microsoft.com/wbem/wsman/1/windows/shell">
<s:Header>
<wsa:To>{url}</wsa:To>
<wsa:ReplyTo><wsa:Address s:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address></wsa:ReplyTo>
<wsa:Action s:mustUnderstand="true">http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Receive</wsa:Action>
<wsman:MaxEnvelopeSize s:mustUnderstand="true">512000</wsman:MaxEnvelopeSize>
<wsa:MessageID>uuid:{str(uuid.uuid4())}</wsa:MessageID>
<wsman:Locale xml:lang="en-US" s:mustUnderstand="false"/>
<wsman:ResourceURI s:mustUnderstand="true">http://schemas.microsoft.com/wbem/wsman/1/windows/shell/cmd</wsman:ResourceURI>
<wsman:SelectorSet>
<wsman:Selector Name="ShellId">{shell_id}</wsman:Selector>
</wsman:SelectorSet>
<wsman:OperationTimeout>PT60S</wsman:OperationTimeout>
</s:Header>
<s:Body>
<rsp:Receive>
<rsp:DesiredStream CommandId="{command_id}">stdout stderr</rsp:DesiredStream>
</rsp:Receive>
</s:Body>
</s:Envelope>'''

            # --- ОТПРАВКА ЗАПРОСА ---
            response = requests.post(url, auth=auth, headers=headers, data=get_output_xml, timeout=self.timeout)

            if response.status_code != 200:
                break

            # --- ПАРСИНГ ОТВЕТА ---
            root = ET.fromstring(response.content)

            # Получаем все Stream элементы с stdout
            for stream_elem in root.findall('.//rsp:Stream[@Name="stdout"]', self.namespaces):
                if stream_elem.text:
                    chunk = base64.b64decode(stream_elem.text).decode('utf-8', errors='ignore')
                    all_output.append(chunk)

            # Проверяем CommandState - если Done, выходим
            cmd_state = root.find('.//rsp:CommandState', self.namespaces)
            if cmd_state is not None:
                state = cmd_state.get('State', '')
                if 'Done' in state:
                    break

            # Ждём перед следующим poll
            time.sleep(3)

        return ''.join(all_output).strip()

# =============================================================================
# КОНЕЦ МОДУЛЯ
# =============================================================================
