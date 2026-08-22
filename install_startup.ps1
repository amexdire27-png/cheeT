# Register PageMind to start hidden at logon (current user, no admin required).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskName = "PageMind"

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
    Write-Error "pythonw.exe not found. Install Python 3.11+ and tick 'Add python.exe to PATH'."
}

$Tray = Join-Path $Root "tray_host.py"
if (-not (Test-Path $Tray)) {
    Write-Error "tray_host.py not found in $Root"
}

$Action = New-ScheduledTaskAction -Execute $PythonW -Argument "`"$Tray`"" -WorkingDirectory $Root
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

Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 400
& wscript.exe //B //Nologo (Join-Path $Root "run_tray.vbs")

Write-Host "Overflow icon starts hidden at logon."
Write-Host "Desktop shortcut Stop: $ShortcutPath"
Write-Host "Overflow tray icon: Sync Host (Start / Restart)"
