# Package the Windows app zip the website hands out (cheeT1.exe folder).
# powershell -ExecutionPolicy Bypass -File .\site\build_download.ps1
$ErrorActionPreference = "Stop"
$Site = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Site
$Out = Join-Path $Site "downloads\cheeT1-v1.zip"

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "build_exe.ps1")

$Packed = Join-Path $Root "dist\cheeT1"
if (-not (Test-Path (Join-Path $Packed "cheeT1.exe"))) {
    throw "dist\cheeT1\cheeT1.exe missing after build_exe.ps1"
}

New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
if (Test-Path $Out) { Remove-Item $Out -Force }
Compress-Archive -Path $Packed -DestinationPath $Out

$size = [math]::Round((Get-Item $Out).Length / 1MB, 1)
Write-Host "Built $Out ($size MB)"
