#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест создания и шифрования Bitcoin Core кошелька с walletversion 60000.

Проверяет:
1. Запуск Bitcoin Core 0.6.1
2. Создание кошелька (автоматически при первом запуске)
3. Проверку версии через bitcoin-cli
4. Шифрование кошелька паролем
5. Разблокировку и генерацию адреса
"""

import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bitcoin_wallet_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# === КОНФИГУРАЦИЯ ===
# Измените эти пути под вашу систему

# Путь к Bitcoin Core 0.6.1
BITCOIN_DIR = Path(r"C:\BitcoinCore-0.6.1")
BITCOIN_QT = BITCOIN_DIR / "bitcoin-qt.exe"
BITCOIN_CLI = BITCOIN_DIR / "bitcoin-cli.exe"

# Путь к datadir (где будет храниться кошелёк)
DATADIR = Path(r"D:\BitcoinData06_Test")

# Тестовый пароль для шифрования
TEST_PASSWORD = "TestPassword123!@#"


class BitcoinWalletTester:
    """Класс для тестирования Bitcoin Core кошелька."""

    def __init__(self, bitcoin_dir: Path, datadir: Path, password: str):
        self.bitcoin_dir = bitcoin_dir
        self.datadir = datadir
        self.password = password
        self.bitcoin_qt = bitcoin_dir / "bitcoin-qt.exe"
        self.bitcoin_cli = bitcoin_dir / "bitcoin-cli.exe"
        self.wallet_path = datadir / "wallet.dat"

        logger.info(f"Bitcoin Core dir: {self.bitcoin_dir}")
        logger.info(f"Data directory: {self.datadir}")
        logger.info(f"Wallet path: {self.wallet_path}")

    def check_prerequisites(self) -> bool:
        """Проверка наличия необходимых файлов."""
        logger.info("Checking prerequisites...")

        if not self.bitcoin_qt.exists():
            logger.error(f"bitcoin-qt.exe not found: {self.bitcoin_qt}")
            return False

        if not self.bitcoin_cli.exists():
            logger.error(f"bitcoin-cli.exe not found: {self.bitcoin_cli}")
            return False

        logger.info("[OK] All files found")
        return True

    def start_bitcoin_core(self) -> Optional[subprocess.Popen]:
        """Запуск Bitcoin Core с отдельным datadir."""
        logger.info("Starting Bitcoin Core...")

        # Создаём datadir если не существует
        self.datadir.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.bitcoin_qt),
            f"-datadir={self.datadir}"
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW  # Без окна консоли
            )
            logger.info(f"Bitcoin Core started (PID: {process.pid})")

            # Ждём пока создастся wallet.dat
            logger.info("Waiting for wallet.dat to be created...")
            timeout = 60  # секунд
            start_time = time.time()

            while time.time() - start_time < timeout:
                if self.wallet_path.exists():
                    logger.info(f"[OK] wallet.dat created: {self.wallet_path}")
                    return process
                time.sleep(2)

            logger.error(f"Timeout: wallet.dat not created within {timeout}s")
            return None

        except Exception as e:
            logger.error(f"Failed to start Bitcoin Core: {e}")
            return None

    def run_cli_command(self, command: str, *args) -> Optional[Dict[str, Any]]:
        """Выполнение команды через bitcoin-cli."""
        cmd = [
            str(self.bitcoin_cli),
            f"-datadir={self.datadir}",
            command
        ] + list(args)

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                return None

            # Пытаемся распарсить как JSON
            try:
                output = json.loads(result.stdout)
                logger.info(f"Response: {json.dumps(output, indent=2)}")
                return output
            except json.JSONDecodeError:
                # Если не JSON, возвращаем как есть
                logger.info(f"Response: {result.stdout.strip()}")
                return {"raw_output": result.stdout.strip()}

        except subprocess.TimeoutExpired:
            logger.error("Command timeout")
            return None
        except Exception as e:
            logger.error(f"Command error: {e}")
            return None

    def check_wallet_version(self) -> Optional[int]:
        """Проверка версии кошелька."""
        logger.info("Checking wallet version...")

        # Пробуем getwalletinfo (может не быть в 0.6.x)
        info = self.run_cli_command("getwalletinfo")
        if info and "walletversion" in info:
            version = info["walletversion"]
            logger.info(f"[OK] Wallet version: {version}")
            return version

        # Пробуем getinfo (старая команда)
        info = self.run_cli_command("getinfo")
        if info and "walletversion" in info:
            version = info["walletversion"]
            logger.info(f"[OK] Wallet version: {version}")
            return version

        logger.error("Could not determine wallet version")
        return None

    def encrypt_wallet(self) -> bool:
        """Шифрование кошелька паролем."""
        logger.info(f"Encrypting wallet with password...")

        result = self.run_cli_command("encryptwallet", self.password)

        if result:
            logger.info("[OK] Wallet encrypted successfully")
            logger.warning("Bitcoin Core will stop after encryption. Need to restart.")
            return True
        else:
            logger.error("Failed to encrypt wallet")
            return False

    def unlock_wallet(self, timeout: int = 60) -> bool:
        """Разблокировка зашифрованного кошелька."""
        logger.info(f"Unlocking wallet for {timeout} seconds...")

        result = self.run_cli_command("walletpassphrase", self.password, str(timeout))

        if result is not None:
            logger.info("[OK] Wallet unlocked")
            return True
        else:
            logger.error("Failed to unlock wallet")
            return False

    def generate_address(self) -> Optional[str]:
        """Генерация нового адреса."""
        logger.info("Generating new address...")

        result = self.run_cli_command("getnewaddress")

        if result and "raw_output" in result:
            address = result["raw_output"]
            logger.info(f"[OK] New address: {address}")
            return address

        logger.error("Failed to generate address")
        return None

    def stop_bitcoin_core(self, process: subprocess.Popen):
        """Остановка Bitcoin Core."""
        logger.info("Stopping Bitcoin Core...")

        # Пробуем через CLI
        self.run_cli_command("stop")

        # Ждём завершения процесса
        try:
            process.wait(timeout=30)
            logger.info("[OK] Bitcoin Core stopped")
        except subprocess.TimeoutExpired:
            logger.warning("Bitcoin Core did not stop gracefully, terminating...")
            process.terminate()
            process.wait(timeout=10)


def main():
    """Основная функция тестирования."""
    print("="*60)
    print("Bitcoin Core Wallet Test (walletversion 60000)")
    print("="*60)
    print()

    tester = BitcoinWalletTester(BITCOIN_DIR, DATADIR, TEST_PASSWORD)

    # Шаг 1: Проверка файлов
    print("Step 1: Checking prerequisites...")
    if not tester.check_prerequisites():
        print("[ERROR] Prerequisites check failed. Check logs.")
        return
    print("[OK] Prerequisites check passed\n")

    # Шаг 2: Запуск Bitcoin Core
    print("Step 2: Starting Bitcoin Core...")
    process = tester.start_bitcoin_core()
    if not process:
        print("[ERROR] Failed to start Bitcoin Core. Check logs.")
        return
    print("[OK] Bitcoin Core started\n")

    # Ждём пока запустится RPC сервер
    print("Waiting for RPC server to start...")
    time.sleep(10)

    # Шаг 3: Проверка версии кошелька
    print("Step 3: Checking wallet version...")
    version = tester.check_wallet_version()
    if version is None:
        print("[ERROR] Could not get wallet version. Check logs.")
        tester.stop_bitcoin_core(process)
        return

    print(f"[OK] Wallet version: {version}")
    if version == 60000:
        print("[SUCCESS] Wallet has correct version 60000!")
    else:
        print(f"[WARNING] Wallet version is {version}, not 60000")
    print()

    # Шаг 4: Шифрование кошелька
    print("Step 4: Encrypting wallet...")
    if not tester.encrypt_wallet():
        print("[ERROR] Failed to encrypt wallet. Check logs.")
        tester.stop_bitcoin_core(process)
        return
    print("[OK] Wallet encrypted\n")

    # После encryptwallet Bitcoin Core останавливается
    print("Bitcoin Core stopped after encryption. Waiting...")
    process.wait()
    time.sleep(5)

    # Шаг 5: Перезапуск Bitcoin Core
    print("Step 5: Restarting Bitcoin Core...")
    process = tester.start_bitcoin_core()
    if not process:
        print("[ERROR] Failed to restart Bitcoin Core. Check logs.")
        return
    print("[OK] Bitcoin Core restarted\n")

    # Ждём RPC
    print("Waiting for RPC server...")
    time.sleep(10)

    # Шаг 6: Разблокировка кошелька
    print("Step 6: Unlocking wallet...")
    if not tester.unlock_wallet():
        print("[ERROR] Failed to unlock wallet. Check logs.")
        tester.stop_bitcoin_core(process)
        return
    print("[OK] Wallet unlocked\n")

    # Шаг 7: Генерация адреса
    print("Step 7: Generating new address...")
    address = tester.generate_address()
    if not address:
        print("[ERROR] Failed to generate address. Check logs.")
        tester.stop_bitcoin_core(process)
        return
    print(f"[OK] Generated address: {address}\n")

    # Финал
    print("="*60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("="*60)
    print()
    print("Summary:")
    print(f"- Wallet version: {version}")
    print(f"- Encrypted: YES")
    print(f"- Password: {TEST_PASSWORD}")
    print(f"- Test address: {address}")
    print(f"- Wallet location: {tester.wallet_path}")
    print()
    print("Make a backup of wallet.dat!")
    print()

    # Остановка
    print("Stopping Bitcoin Core...")
    tester.stop_bitcoin_core(process)
    print("[OK] Test finished")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test stopped by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n[ERROR] {e}")
