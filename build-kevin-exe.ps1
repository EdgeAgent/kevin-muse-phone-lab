$ErrorActionPreference = 'Stop'
python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean --onefile --name kevin-phone-worker phone_worker.py
pyinstaller --noconfirm --clean --onefile --name kevin-server --add-data "public;public" server.py
Copy-Item "dist\kevin-phone-worker.exe" ".\kevin-phone-worker.exe" -Force
Copy-Item "dist\kevin-server.exe" ".\kevin-server.exe" -Force
Write-Host "Built kevin-server.exe and kevin-phone-worker.exe. Run run-kevin-windows.bat."
