# Полное удаление ClawdBot с VPS 195.177.94.189
# Запуск: .\REMOVE_CLAWDBOT.ps1
# Требуется: ввести пароль при запросе SSH

$VPS = "195.177.94.189"
$User = "root"

$Commands = @"
echo '=== Stopping ClawdBot ==='
systemctl stop clawdbot 2>/dev/null || true
systemctl disable clawdbot 2>/dev/null || true
echo '=== Removing systemd service ==='
rm -f /etc/systemd/system/clawdbot.service
systemctl daemon-reload
echo '=== Removing /opt/clawdbot ==='
rm -rf /opt/clawdbot
echo '=== Checking ==='
ls -la /opt/ 2>/dev/null | grep -E 'clawdbot|total' || true
systemctl status clawdbot 2>&1 | head -3 || true
echo ''
echo 'DONE: ClawdBot fully removed.'
"@

Write-Host "Connecting to $User@$VPS and removing ClawdBot..."
Write-Host "You may be prompted for SSH password."
Write-Host ""

# One-line for SSH
$OneLine = $Commands -replace "`r`n", " ; "

& ssh -o StrictHostKeyChecking=no "${User}@${VPS}" $OneLine

Write-Host ""
Write-Host "Script finished."
