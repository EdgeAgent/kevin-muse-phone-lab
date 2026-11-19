$ErrorActionPreference = 'Stop'

function Say($Text) { Write-Host "[PhoneOps Android] $Text" -ForegroundColor Cyan }
function Warn($Text) { Write-Host "[PhoneOps Android] $Text" -ForegroundColor Yellow }

$Sdk = $env:ANDROID_HOME
if (-not $Sdk) { $Sdk = $env:ANDROID_SDK_ROOT }
if (-not $Sdk) { $Sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk' }
$SdkManager = Join-Path $Sdk 'cmdline-tools\latest\bin\sdkmanager.bat'
if (-not (Test-Path $SdkManager)) { $SdkManager = Join-Path $Sdk 'tools\bin\sdkmanager.bat' }
$AvdManager = Join-Path $Sdk 'cmdline-tools\latest\bin\avdmanager.bat'
if (-not (Test-Path $AvdManager)) { $AvdManager = Join-Path $Sdk 'tools\bin\avdmanager.bat' }
$Emulator = Join-Path $Sdk 'emulator\emulator.exe'
$Adb = Join-Path $Sdk 'platform-tools\adb.exe'

if (-not (Test-Path $SdkManager)) {
  throw "Android command-line tools were not found at $Sdk. Open Android Studio > SDK Manager and install Android SDK Command-line Tools (latest), then run this script again."
}
if (-not (Test-Path $AvdManager)) { throw "avdmanager was not found. Install Android SDK Command-line Tools (latest) in Android Studio." }

$env:ANDROID_HOME = $Sdk
$env:ANDROID_SDK_ROOT = $Sdk
$env:Path = "$Sdk\platform-tools;$Sdk\emulator;$Sdk\cmdline-tools\latest\bin;$env:Path"

Say "Using Android SDK: $Sdk"
Say "Installing Platform-Tools, Emulator, API 35, and the Google Play x86_64 image."
Write-Host ""
Warn "Android requires explicit license acceptance. Review and accept the licenses now."
& $SdkManager --licenses
& $SdkManager 'platform-tools' 'emulator' 'platforms;android-35' 'system-images;android-35;google_apis_playstore;x86_64'

$avdName = 'PhoneOps-01'
$package = 'system-images;android-35;google_apis_playstore;x86_64'
$existing = & $AvdManager list avd 2>$null | Select-String "Name:","$avdName"
if (-not ($existing -match $avdName)) {
  Say "Creating $avdName with the Google Play image."
  $yes = "no`n" | & $AvdManager create avd -n $avdName -k $package -d pixel_7 --force
} else {
  Say "$avdName already exists; keeping the existing AVD data."
}

if (-not (Test-Path $Emulator)) { throw "The emulator executable was not found after installation: $Emulator" }
Say "Google Play AVD ready: $avdName"
Say "Launching the emulator. The first boot may take several minutes."
Start-Process -FilePath $Emulator -ArgumentList "@$avdName -no-boot-anim" -WorkingDirectory (Split-Path $Emulator)

if (Test-Path $Adb) {
  Say "ADB is available at $Adb"
  Say "After Android finishes booting, verify Chrome and Play Store with:"
  Write-Host "  & '$Adb' shell pm list packages | Select-String 'com.android.chrome|com.android.vending'"
  Write-Host "Expected: com.android.chrome and com.android.vending"
}
Write-Host ""
Say "Open PhoneOps and check Real Android Mode."
Read-Host 'Press Enter to close'
