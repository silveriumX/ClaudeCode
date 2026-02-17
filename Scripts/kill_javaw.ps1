# Kill javaw.exe (and jawaw if typo) — run when Java process burns traffic
$names = @('javaw', 'jawaw')
foreach ($n in $names) {
    $procs = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | ForEach-Object { Write-Host "Killing PID $($_.Id): $($_.Path)" }
        $procs | Stop-Process -Force
    }
}
if (-not (Get-Process -Name $names -ErrorAction SilentlyContinue)) {
    Write-Host "No javaw/jawaw processes found (already stopped or not running)."
}
