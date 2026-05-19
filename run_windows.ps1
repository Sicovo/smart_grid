$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"

$lanIp = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*' -and
        $_.InterfaceAlias -eq 'WiFi'
    } |
    Select-Object -ExpandProperty IPAddress -First 1

if (-not $lanIp) {
    $lanIp = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*'
        } |
        Select-Object -ExpandProperty IPAddress -First 1
}

if (Test-Path $backendPython) {
    $pythonCommand = "& '$backendPython'"
} else {
    $pythonCommand = "python"
}

$backendCommand = "Set-Location '$backendDir'; $pythonCommand -m uvicorn main:app --reload --host 0.0.0.0"
$frontendCommand = "Set-Location '$frontendDir'; npm.cmd run dev"

Start-Process powershell.exe -WorkingDirectory $backendDir -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-Command', $backendCommand
)

Start-Process powershell.exe -WorkingDirectory $frontendDir -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-Command', $frontendCommand
)

Write-Host "Started backend and frontend in separate PowerShell windows."
if ($lanIp) {
    Write-Host "Frontend URL: http://$lanIp`:5173"
    Write-Host "Backend URL:  http://$lanIp`:8000"
} else {
    Write-Host "Could not detect a LAN IP automatically. Run Get-NetIPAddress -AddressFamily IPv4 and use your Wi-Fi IPv4 address."
}