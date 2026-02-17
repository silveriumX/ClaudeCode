# Load .env file
$envFile = Join-Path $PSScriptRoot "..\..\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}
param(
    [string]$Command
)

$server = "195.177.94.189"
$username = "root"
$password = $env:VPS_LINUX_PASSWORD

# Создаем SecureString пароль
$securePassword = ConvertTo-SecureString $password -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($username, $securePassword)

# Выполняем команду через SSH
$sshCommand = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${username}@${server} `"$Command`""

# Используем plink если доступен, иначе обычный SSH
try {
    # Пробуем через обычный SSH с expect-подобным поведением
    $env:SSH_ASKPASS = "echo $password"
    $env:DISPLAY = ":0"

    # Создаем временный скрипт для автоматического ввода пароля
    $expectScript = @"
`$password = "$password"
`$pinfo = New-Object System.Diagnostics.ProcessStartInfo
`$pinfo.FileName = "ssh"
`$pinfo.RedirectStandardError = `$true
`$pinfo.RedirectStandardOutput = `$true
`$pinfo.RedirectStandardInput = `$true
`$pinfo.UseShellExecute = `$false
`$pinfo.Arguments = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${username}@${server} '$Command'"
`$p = New-Object System.Diagnostics.Process
`$p.StartInfo = `$pinfo
`$p.Start() | Out-Null

# Ждем запрос пароля и отправляем его
Start-Sleep -Milliseconds 500
`$p.StandardInput.WriteLine(`$password)
`$p.StandardInput.Close()

`$stdout = `$p.StandardOutput.ReadToEnd()
`$stderr = `$p.StandardError.ReadToEnd()
`$p.WaitForExit()

Write-Output `$stdout
if (`$stderr) {
    Write-Error `$stderr
}
"@

    Invoke-Expression $expectScript
}
catch {
    Write-Error "Failed to execute SSH command: $_"
    exit 1
}
