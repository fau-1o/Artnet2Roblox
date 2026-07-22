@echo off
chcp 65001 >nul
title Install Dependensi - Artnet2Roblox
cd /d "%~dp0"

echo ============================================================
echo   Install Dependensi Python - Artnet2Roblox
echo ============================================================
echo.

rem Utamakan "py" (Python Launcher, biasanya menunjuk ke versi terbaru
rem yang terinstall), baru fallback ke "python" kalau py tidak ada.
set PY_CMD=py
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python tidak ditemukan di PATH.
        echo.
        echo Silakan install Python dari https://www.python.org/downloads/
        echo PENTING: centang "Add Python to PATH" saat instalasi.
        echo.
        pause
        exit /b 1
    ) else (
        set PY_CMD=python
    )
)

echo Menggunakan perintah: %PY_CMD%
%PY_CMD% --version
echo.

echo Meng-upgrade pip...
%PY_CMD% -m pip install --upgrade pip
echo.

echo Menginstall dependensi dari requirements.txt ...
%PY_CMD% -m pip install -r "requirements.txt"

if errorlevel 1 (
    echo.
    echo [ERROR] Instalasi gagal. Periksa pesan error di atas.
    pause
    exit /b 1
)

echo ok > ".deps_installed"

echo.
echo ============================================================
echo   Semua dependensi berhasil terinstall!
echo   Selanjutnya jalankan:
echo     2_JALANKAN_SERVER.bat        (buka dulu, biarkan terbuka)
echo     3_JALANKAN_ARTNET2WSS.bat    (buka setelah server jalan)
echo   Atau cukup jalankan START_SEMUA.bat untuk sekali klik.
echo ============================================================
pause
