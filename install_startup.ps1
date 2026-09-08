# Register PageMind to start hidden at logon (current user, no admin required).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskName = "PageMind"
$Exe = Join-Path $Root "cheeT1.exe"

$Config = Join-Path $Root "config.json"
$Example = Join-Path $Root "config.example.json"
if (-not (Test-Path $Config) -and (Test-Path $Example)) {
    Copy-Item $Example $Config
}

if (Test-Path $Exe) {
    & $Exe --install
    Write-Host "Overflow icon starts hidden at logon."
    Write-Host "Desktop: cheeT1 (settings) and Sync Host (Stop)"
    Write-Host "Search and Start menu: cheeT1 / Chee"
    return
}

$PythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonW)) {
    $cmd = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($cmd) { $PythonW = $cmd.Source }
}
if (-not $PythonW -or -not (Test-Path $PythonW)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PythonW = $cmd.Source }
}
if (-not $PythonW) {
    Write-Error "pythonw.exe not found. Run setup.cmd (or setup.ps1) first. Install Python 3.11+ and tick 'Add python.exe to PATH'."
}

$Launch = Join-Path $Root "launch.py"
$TrayArg = if (Test-Path $Launch) { "`"$Launch`" --tray" } else { "`"$(Join-Path $Root 'tray_host.py')`"" }
$SettingsArg = if (Test-Path $Launch) { "`"$Launch`"" } else { "`"$(Join-Path $Root 'app.py')`"" }

$Action = New-ScheduledTaskAction -Execute $PythonW -Argument $TrayArg -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -Hidden `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null

$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Item -ItemType Directory -Force -Path $StartMenu | Out-Null

$ShortcutPath = Join-Path $Desktop "Sync Host.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$env:SystemRoot\System32\wscript.exe"
$Shortcut.Arguments = "//B //Nologo `"$Root\stop_host.vbs`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle = 7
$Shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,15"
$Shortcut.Description = "Synchronizes host cache"
$Shortcut.Save()

function Save-CheeShortcut([string]$Path) {
    $link = $Wsh.CreateShortcut($Path)
    $link.TargetPath = $PythonW
    $link.Arguments = $SettingsArg
    $link.WorkingDirectory = $Root
    $link.WindowStyle = 1
    $link.Description = "Chee — on-screen assistant (cheeT1)"
    if (Test-Path $AppIco) {
        $link.IconLocation = $AppIco
    }
    $link.Save()
}

$AppIco = Join-Path $Root "assets\app.ico"
Save-CheeShortcut (Join-Path $Desktop "cheeT1.lnk")
Save-CheeShortcut (Join-Path $StartMenu "cheeT1.lnk")
Save-CheeShortcut (Join-Path $StartMenu "Chee.lnk")

Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 400
& wscript.exe //B //Nologo (Join-Path $Root "run_tray.vbs")

Write-Host "Overflow icon starts hidden at logon."
Write-Host "Desktop shortcut Stop: $ShortcutPath"
Write-Host "Search and Start menu: cheeT1 / Chee"
Write-Host "Overflow tray icon: Sync Host (Start / Restart)"
