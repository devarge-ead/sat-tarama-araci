@echo off
REM Build a portable single-file executable with PyInstaller.
setlocal

cd /d "%~dp0"

echo Building SAT Tarama Araci portable exe...

.venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "SAT Tarama Araci" ^
    --icon "assets\app.ico" ^
    --add-data "assets\app.ico;assets" ^
    --hidden-import "xlrd" ^
    --hidden-import "openpyxl" ^
    run_app.py

echo.
echo Build complete. Output: dist\SAT Tarama Araci.exe
endlocal