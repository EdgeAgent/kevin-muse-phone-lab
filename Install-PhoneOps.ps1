$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Has-Command($Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }
function Say($Text) { Write-Host "[PhoneOps] $Text" -ForegroundColor Cyan }
function Warn($Text) { Write-Host "[PhoneOps] $Text" -ForegroundColor Yellow }

Say "Installing PhoneOps by EDGE | AGENCY"
Say "Project folder: $Root"

if ($env:OS -ne 'Windows_NT') { throw 'This one-click installer is for Windows. Use the documented Python launcher on Linux.' }

# The packaged EXE path avoids requiring Python for normal users.
if (-not (Test-Path (Join-Path $Root 'kevin-server.exe'))) {
  Warn 'Packaged EXEs are not present. Preparing a source launch instead.'
  $python = $null
  if (Has-Command py) { $python = 'py' } elseif (Has-Command python) { $python = 'python' }
  if (-not $python) {
    if (Has-Command winget) {
      Say 'Python is missing. Installing Python 3.12 through Windows Package Manager.'
      winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
      Warn 'Close and reopen this installer after Python finishes so Windows refreshes PATH.'
      exit 0
    }
    throw 'Python is missing and winget is unavailable. Install Python 3.12, then run this installer again.'
  }
  Say 'Building local PhoneOps executables. This is only needed for a source checkout.'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'build-kevin-exe.ps1')
}

# Android Studio is optional, but recommended for actual Android AVDs.
$androidStudio = Join-Path $env:ProgramFiles 'Android\Android Studio\bin\studio64.exe'
$androidStudioAlt = Join-Path ${env:ProgramFiles(x86)} 'Android\Android Studio\bin\studio64.exe'
if (-not (Test-Path $androidStudio) -and -not (Test-Path $androidStudioAlt)) {
  $answer = Read-Host 'Android Studio was not found. Install it now with winget? [Y/n]'
  if ($answer -notmatch '^[Nn]') {
    if (Has-Command winget) {
      winget install --id Google.AndroidStudio -e --accept-package-agreements --accept-source-agreements
      Say 'Android Studio installed. Open it once to finish SDK and AVD setup.'
    } else {
      Warn 'winget is unavailable. Install Android Studio manually from https://developer.android.com/studio'
    }
  }
}

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'PhoneOps.lnk'
$startScript = Join-Path $Root 'Start-PhoneOps.bat'
$wsh = New-Object -ComObject WScript.Shell
$link = $wsh.CreateShortcut($shortcutPath)
$link.TargetPath = $startScript
$link.WorkingDirectory = $Root
$link.IconLocation = (Join-Path $Root 'kevin-server.exe')
$link.Description = 'PhoneOps — local phone agent operations by EDGE | AGENCY'
$link.Save()

$webSetup = Join-Path $Root 'Setup-PhoneOps-Web.bat'
if (Test-Path $webSetup) {
  $webLink = $wsh.CreateShortcut((Join-Path $desktop 'PhoneOps — Setup Web Browsers.lnk'))
  $webLink.TargetPath = $webSetup
  $webLink.WorkingDirectory = $Root
  $webLink.Description = 'Install isolated per-phone web browser sessions for PhoneOps'
  $webLink.Save()
}

$androidSetup = Join-Path $Root 'Setup-PhoneOps-GooglePlay.bat'
if (Test-Path $androidSetup) {
  $androidLink = $wsh.CreateShortcut((Join-Path $desktop 'PhoneOps — Setup Google Play.lnk'))
  $androidLink.TargetPath = $androidSetup
  $androidLink.WorkingDirectory = $Root
  $androidLink.Description = 'Install and launch the PhoneOps Google Play Android Virtual Device'
  $androidLink.Save()
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root 'downloads') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null

Say 'Setup complete.'
Say 'A PhoneOps shortcut was created on your desktop.'
Say 'Start PhoneOps from the desktop shortcut, then open http://localhost:8787.'
if ((Test-Path $androidStudio) -or (Test-Path $androidStudioAlt)) {
  Say 'Android Studio detected. Create at least one PhoneOps AVD in Device Manager for real Android mode.'
} else {
  Warn 'Android Studio is not installed; PhoneOps will use its safe local worker fallback until it is installed.'
}
Read-Host 'Press Enter to close'
