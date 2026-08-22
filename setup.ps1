# One-step setup for a new Windows 10/11 PC. No admin required.
# Double-click setup.cmd  or:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Test-RealPython([string]$Exe, [string[]]$Prefix) {
    if (-not $Exe) { return $false }
    if ($Exe -match "WindowsApps") { return $false }
    try {
        $out = & $Exe @($Prefix + "--version") 2>&1 | Out-String
        if ($out -notmatch "Python (\d+)\.(\d+)") { return $false }
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        return ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11))
    } catch {
        return $false
    }
}

function Find-Python {
    Refresh-Path
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py -and (Test-RealPython $py.Source @("-3"))) {
        return @{ Exe = $py.Source; Prefix = @("-3") }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and (Test-RealPython $cmd.Source @())) {
            return @{ Exe = $cmd.Source; Prefix = @() }
        }
    }
    $guesses = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($path in $guesses) {
        if (Test-Path $path) {
            return @{ Exe = $path; Prefix = @() }
        }
    }
    return $null
}

function Install-Python {
    Write-Host "Python 3.11+ not found. Installing Python 3.12 (App Installer / winget)..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw @"
Python is missing and winget is not available.
Install Python 3.11+ from https://www.python.org/downloads/
Tick "Add python.exe to PATH", then run setup.cmd again.
"@
    }
    & winget.exe install --id Python.Python.3.12 -e --source winget `
        --accept-package-agreements --accept-source-agreements --disable-interactivity
    Start-Sleep -Seconds 2
    Refresh-Path
}

function Show-Hotkeys {
    $path = Join-Path $Root "config.json"
    if (-not (Test-Path $path)) {
        $path = Join-Path $Root "config.example.json"
    }
    try {
        $cfg = Get-Content $path -Raw | ConvertFrom-Json
        $h = $cfg.hotkeys
        Write-Host "Hotkeys (edit in config.json, then overflow Restart):"
        Write-Host "  Picture  $($h.screenshot)"
        Write-Host "  Text     $($h.ocr)"
        Write-Host "  Dismiss  $($h.dismiss)"
        Write-Host "  Abort    $($h.abort)"
        Write-Host "  Start    $($h.start)"
        Write-Host "  Restart  $($h.restart)"
    } catch {
        Write-Host "Hotkeys are in config.json under 'hotkeys'."
    }
}

function Test-ApiKey([string]$ConfigPath) {
    if (-not (Test-Path $ConfigPath)) { return $false }
    try {
        $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        $keys = @()
        if ($cfg.api_keys) { $keys += @($cfg.api_keys) }
        if ($cfg.api_key) { $keys += [string]$cfg.api_key }
        if ($cfg.backup_api_key) { $keys += [string]$cfg.backup_api_key }
        foreach ($key in $keys) {
            $text = [string]$key
            if ($text.Length -gt 8 -and -not $text.ToUpper().StartsWith("YOUR_")) {
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

Write-Host "Setting up Sync Host in $Root"

Get-ChildItem $Root -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in ".ps1", ".vbs", ".cmd" } |
    Unblock-File -ErrorAction SilentlyContinue

Refresh-Path
$Python = Find-Python
if (-not $Python) {
    Install-Python
    $Python = Find-Python
}
if (-not $Python) {
    throw @"
Python 3.11+ is still not available.
1. Install from https://www.python.org/downloads/
2. Tick "Add python.exe to PATH"
3. Close this window and double-click setup.cmd again.
"@
}

$version = (& $Python.Exe @($Python.Prefix + "--version") 2>&1 | Out-String).Trim()
Write-Host "Using $version"

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$VenvPythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating .venv ..."
    & $Python.Exe @($Python.Prefix + @("-m", "venv", ".venv"))
}
if (-not (Test-Path $VenvPython)) {
    throw "venv was not created. Reinstall Python 3.11+ with 'Add python.exe to PATH', then run setup.cmd again."
}

Write-Host "Installing packages ..."
& $VenvPython -m pip install --upgrade pip --disable-pip-version-check
& $VenvPython -m pip install -r (Join-Path $Root "requirements.txt") --prefer-binary --disable-pip-version-check

$PostInstall = Join-Path $Root ".venv\Scripts\pywin32_postinstall.py"
if (Test-Path $PostInstall) {
    & $VenvPython $PostInstall -install 2>$null | Out-Null
}

Write-Host "Checking packages ..."
& $VenvPython -c "import mss, pynput, pystray, win32gui, PIL, requests, pyperclip"

$Config = Join-Path $Root "config.json"
$Example = Join-Path $Root "config.example.json"
if (-not (Test-Path $Config)) {
    Copy-Item $Example $Config
    Write-Host "Created config.json."
}

if (-not (Test-Path $VenvPythonW)) {
    Copy-Item $VenvPython $VenvPythonW -ErrorAction SilentlyContinue
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "install_startup.ps1")

Start-Sleep -Milliseconds 500
if (Test-ApiKey $Config) {
    & wscript.exe //B //Nologo (Join-Path $Root "run_hidden.vbs")
    Write-Host "Host started."
} else {
    Write-Host "No API key yet. Opening config.json — paste keys into api_keys, save, then overflow Start."
    Start-Process notepad.exe $Config
}

Write-Host ""
Write-Host "Setup finished."
Write-Host "Overflow (^) Sync Host: Start / Restart. Desktop Sync Host: Stop."
Show-Hotkeys
Write-Host "Log: $env:LOCALAPPDATA\.cache\syshelper\logs\pagemind.log"
