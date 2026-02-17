#!/usr/bin/env python3
"""
=============================================================================
SSH CONNECTOR - Модуль для выполнения команд через SSH
=============================================================================
Описание:
- Подключается к Windows серверам через SSH (порт 22)
- Выполняет PowerShell команды удалённо
- Использует password аутентификацию
- Намного стабильнее и быстрее чем WinRM
Версия: 1.0
Дата: 26.01.2026
=============================================================================
"""

import logging
import paramiko
import time

logger = logging.getLogger(__name__)

class SSHConnector:
    """
    Класс для выполнения PowerShell команд на удалённых Windows серверах через SSH

    Преимущества перед WinRM:
    - Стабильное подключение (не ломается)
    - Быстрое выполнение команд
    - Простой протокол
    - Надёжная передача данных
    """

    def __init__(self, timeout=30):
        """
        Инициализация SSH коннектора

        Args:
            timeout (int): Таймаут подключения в секундах (по умолчанию 30)
        """
        self.timeout = 60  # Увеличен timeout для длинных PowerShell команд
        self.connect_timeout = 15  # Timeout для установки соединения

    def execute_command(self, ip, username, password, ps_command, retries=3):
        """
        Выполняет PowerShell команду на удалённом Windows сервере через SSH

        Args:
            ip (str): IP адрес Windows сервера
            username (str): Имя пользователя Windows
            password (str): Пароль пользователя
            ps_command (str): PowerShell команда для выполнения
            retries (int): Количество попыток при ошибке (по умолчанию 3)

        Returns:
            str or None: Результат выполнения команды или None при ошибке

        Example:
            >>> connector = SSHConnector()
            >>> result = connector.execute_command(
            ...     '192.168.1.1',
            ...     'Administrator',
            ...     'password',
            ...     'Get-Process | Select-Object -First 5'
            ... )
        """
        last_error = None

        for attempt in range(retries):
            client = None
            try:
                if attempt > 0:
                    logger.info(f"Retry {attempt + 1}/{retries} for {ip}")
                    time.sleep(2)  # Пауза перед повтором

                # --- ПОДКЛЮЧЕНИЕ ---
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    ip,
                    username=username,
                    password=password,
                    timeout=self.connect_timeout,
                    look_for_keys=False,
                    allow_agent=False
                )

                # --- ВЫПОЛНЕНИЕ КОМАНДЫ ---
                # Для многострочных команд используем -EncodedCommand
                # Кодируем PowerShell команду в Base64 UTF-16LE
                import base64
                encoded_cmd = base64.b64encode(ps_command.encode('utf-16le')).decode('ascii')
                full_command = f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded_cmd}'

                stdin, stdout, stderr = client.exec_command(full_command, timeout=self.timeout)

                # --- ПОЛУЧЕНИЕ РЕЗУЛЬТАТА ---
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                error = stderr.read().decode('utf-8', errors='ignore').strip()

                if error and not output:
                    logger.warning(f"SSH stderr for {ip}: {error[:200]}")

                return output if output else None

            except paramiko.AuthenticationException as e:
                # Ошибка авторизации - retry бесполезен
                logger.error(f"SSH auth failed for {ip}")
                return None
            except (paramiko.SSHException, Exception) as e:
                last_error = e
                logger.warning(f"SSH error for {ip} (attempt {attempt + 1}/{retries}): {e}")

                # Если это последняя попытка - логируем как ошибку
                if attempt == retries - 1:
                    logger.error(f"SSH connection failed for {ip} after {retries} attempts: {last_error}")

            finally:
                if client:
                    try:
                        client.close()
                    except:
                        pass

        # После всех попыток
        return None

# =============================================================================
# КОНЕЦ МОДУЛЯ
# =============================================================================
