#!/usr/bin/env python3
"""
Проверка окон Proxifier - есть ли диалоги, модальные окна
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import base64, io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

def ssh(cmd, timeout=30):
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(os.getenv("VPS_WIN_HOST"), username='Administrator', password=os.getenv("VPS_WIN_PASSWORD"), timeout=10, look_for_keys=False)
        enc = base64.b64encode(cmd.encode('utf-16le')).decode()
        _, o, _ = c.exec_command(f'powershell.exe -NoProfile -NonInteractive -EncodedCommand {enc}', timeout=timeout)
        return o.read().decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return f"ERROR: {e}"


print("="*70)
print("🔍 ПРОВЕРКА ОКОН PROXIFIER")
print("="*70)

# Поиск всех окон от процесса Proxifier
print("\n📋 Все окна от Proxifier.exe:")
print(ssh(r'''
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class WinAPI {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
}
"@

$proxifierPid = (Get-Process Proxifier -ErrorAction SilentlyContinue).Id
if (-not $proxifierPid) {
    Write-Output "Proxifier not running"
    exit
}

Write-Output "Proxifier PID: $proxifierPid"
Write-Output ""

$windows = @()
$callback = [WinAPI+EnumWindowsProc]{
    param($hwnd, $lparam)

    $processId = 0
    [WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$processId) | Out-Null

    if ($processId -eq $proxifierPid) {
        $length = [WinAPI]::GetWindowTextLength($hwnd)
        $sb = New-Object System.Text.StringBuilder($length + 1)
        [WinAPI]::GetWindowText($hwnd, $sb, $sb.Capacity) | Out-Null

        $classSb = New-Object System.Text.StringBuilder(256)
        [WinAPI]::GetClassName($hwnd, $classSb, 256) | Out-Null

        $visible = [WinAPI]::IsWindowVisible($hwnd)

        Write-Output "Handle: $hwnd"
        Write-Output "  Title: $($sb.ToString())"
        Write-Output "  Class: $($classSb.ToString())"
        Write-Output "  Visible: $visible"
        Write-Output ""
    }

    return $true
}

[WinAPI]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
'''))

# Проверка системного трея
print("\n📋 Проверка иконки в трее:")
print(ssh(r'''
$trayWindows = Get-Process | Where-Object {$_.MainWindowTitle -match "Proxifier|proxy"} | Select-Object ProcessName, MainWindowTitle, MainWindowHandle

if ($trayWindows) {
    $trayWindows | Format-Table
} else {
    Write-Output "No windows with 'Proxifier' in title"
}

# Альтернативная проверка - через shell
Get-Process Proxifier -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, @{N='HasWindow';E={$_.MainWindowHandle -ne 0}}
'''))

print("\n" + "="*70)
print("""
📊 ВЫВОДЫ:
- Если есть окно с Title содержащим "Registration" или "License"
  → Proxifier ждёт активации
- Если Visible: False для всех окон
  → Proxifier в трее, но возможно не настроен
- Если вообще нет окон
  → Proxifier запущен но без UI
""")
