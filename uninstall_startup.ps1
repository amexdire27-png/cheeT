# Stop PageMind's logon task if it exists.
$ErrorActionPreference = "SilentlyContinue"
$TaskName = "PageMind"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $Root "cheeT1.exe"

if (Test-Path $Exe) {
    & $Exe --uninstall
    Write-Host "Removed scheduled task, host, tray, and shortcuts."
    return
}

Stop-ScheduledTask -TaskName $TaskName | Out-Null
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
& wscript.exe //B //Nologo (Join-Path $Root "stop_host.vbs")
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'tray_host\.py|launch\.py" --tray|launch\.py --tray' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "Removed scheduled task '$TaskName' (if it existed)."
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
foreach ($name in @("Sync Host.lnk", "cheeT1.lnk", "Chee.lnk")) {
    foreach ($folder in @($Desktop, $StartMenu)) {
        $ShortcutPath = Join-Path $folder $name
        if (Test-Path $ShortcutPath) {
            Remove-Item $ShortcutPath -Force
            Write-Host "Removed shortcut: $ShortcutPath"
        }
    }
}
