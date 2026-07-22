@echo off
chcp 65001 >nul
title Artnet2Roblox - Launcher (Sekali Klik)
cd /d "%~dp0"

echo ============================================================
echo   Artnet2Roblox - Launcher Sekali Klik
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
        echo Silakan install Python dari https://www.python.org/downloads/
        echo PENTING: centang "Add Python to PATH" saat instalasi.
        echo.
        pause
        exit /b 1
    ) else (
        set PY_CMD=python
    )
)

if not exist ".deps_installed" (
    echo Dependensi belum terinstall. Menginstall sekarang...
    %PY_CMD% -m pip install --upgrade pip
    %PY_CMD% -m pip install -r "requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERROR] Gagal install dependensi. Periksa pesan error di atas.
        pause
        exit /b 1
    )
    echo ok > ".deps_installed"
    echo Dependensi berhasil diinstall.
) else (
    echo Dependensi sudah pernah terinstall, dilewati.
    echo ^(Hapus file .deps_installed di folder ini jika ingin install ulang^)
)

echo.
echo [Diagnostik]
echo   Interpreter dipakai : %PY_CMD%
where %PY_CMD%
%PY_CMD% --version
echo   Folder proyek       : %cd%
echo.

echo Menjalankan server.py di jendela baru...
start "Art-Net Bridge Server" cmd /k %PY_CMD% server.py

echo Menunggu server siap...
timeout /t 2 /nobreak >nul

echo Menjalankan artnet2WSS.py di jendela baru...
start "Art-Net to WSS (GUI)" cmd /k %PY_CMD% artnet2WSS.py

echo.
echo ============================================================
echo   Selesai! Kedua program berjalan di jendela terpisah:
echo     1. Art-Net Bridge Server   (jangan ditutup selama main)
echo     2. Art-Net to WSS (GUI)    (isi username Roblox-mu di sini)
echo.
echo   Jendela launcher ini boleh ditutup.
echo ============================================================
pause
