# Stop PageMind's logon task if it exists.
$ErrorActionPreference = "SilentlyContinue"
$TaskName = "PageMind"
Stop-ScheduledTask -TaskName $TaskName | Out-Null
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& wscript.exe //B //Nologo (Join-Path $Root "stop_host.vbs")
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'tray_host\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "Removed scheduled task '$TaskName' (if it existed)."
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Sync Host.lnk"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed desktop shortcut: $ShortcutPath"
}
