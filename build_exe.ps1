# Build cheeT1.exe (one-folder PyInstaller). No console window.
# powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Create .venv first: run setup.cmd, then this script."
}

Write-Host "Installing PyInstaller ..."
& $Python -m pip install --upgrade pyinstaller --disable-pip-version-check

$Icon = Join-Path $Root "assets\app.ico"
$Dist = Join-Path $Root "dist"
$Work = Join-Path $Root "build"

$Data = @(
    "assets\app.ico;assets",
    "assets\logo.png;assets",
    "assets\logo.jpg;assets",
    "assets\logo_dark.png;assets",
    "assets\mark.png;assets",
    "config.example.json;."
)
$AddData = @()
foreach ($item in $Data) {
    $src = ($item -split ";", 2)[0]
    if (Test-Path (Join-Path $Root $src)) {
        $AddData += "--add-data"
        $AddData += $item
    }
}

$Hidden = @(
    "app", "main", "tray", "tray_host", "runtime", "status_toast",
    "ai", "brand", "capture", "config", "hotkeys", "notify", "utils", "widgets",
    "PIL.Image", "PIL.ImageDraw", "PIL.ImageTk", "PIL.ImageFont",
    "pystray._win32", "pynput.keyboard._win32", "pynput.mouse._win32",
    "win32timezone", "win32com.client", "pythoncom", "pywintypes",
    "tkinter", "tkinter.ttk", "tkinter.font"
)
$HiddenArgs = @()
foreach ($name in $Hidden) {
    $HiddenArgs += "--hidden-import"
    $HiddenArgs += $name
}

Write-Host "Building cheeT1.exe ..."
& $Python -m PyInstaller `
    --noconfirm --clean --windowed --onedir `
    --name cheeT1 `
    --icon $Icon `
    --distpath $Dist `
    --workpath $Work `
    --collect-all pynput `
    --collect-all pystray `
    @HiddenArgs `
    @AddData `
    (Join-Path $Root "launch.py")

$OutDir = Join-Path $Dist "cheeT1"
if (-not (Test-Path (Join-Path $OutDir "cheeT1.exe"))) {
    throw "Build failed — dist\cheeT1\cheeT1.exe is missing."
}

Copy-Item (Join-Path $Root "config.example.json") (Join-Path $OutDir "config.example.json") -Force
Copy-Item (Join-Path $Root "uninstall_startup.ps1") (Join-Path $OutDir "uninstall_startup.ps1") -Force
@"
cheeT1
======
1. Unzip this folder anywhere (Desktop is fine).
2. Double-click cheeT1.exe
3. Paste your Gemini key, set hotkeys, click Activate.

No Python install. Settings stay in config.json next to the exe.
Desktop Sync Host stops the background service. The tray icon stays so you can start again.
"@ | Set-Content -Path (Join-Path $OutDir "README.txt") -Encoding UTF8

Write-Host "Built $(Join-Path $OutDir 'cheeT1.exe')"
