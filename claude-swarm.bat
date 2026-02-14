@echo off
REM Запуск Claude Code с активированным Swarm режимом
REM
REM Этот скрипт активирует многоагентный режим в Claude Code
REM Просто запустите: claude-swarm.bat

echo ========================================
echo   Claude Code - SWARM MODE ACTIVATED
echo ========================================
echo.

set "NODE_OPTIONS=--import %USERPROFILE%\.claude\injectors\feature-flag-bypass-pure.mjs"

REM Запуск Claude Code с флагами
claude %*

REM Если нужно запустить в тихом режиме (без логов):
REM set "BYPASS_SILENT=1"
REM set "NODE_OPTIONS=--import %USERPROFILE%\.claude\injectors\feature-flag-bypass-pure.mjs"
REM claude %*
