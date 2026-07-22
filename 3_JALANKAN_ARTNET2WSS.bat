@echo off
chcp 65001 >nul
title Art-Net to WebSocket (GUI)
cd /d "%~dp0"

rem Utamakan "py" (Python Launcher, biasanya menunjuk ke versi terbaru
rem yang terinstall), baru fallback ke "python" kalau py tidak ada.
set PY_CMD=py
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python tidak ditemukan di PATH.
        echo Jalankan dulu 1_INSTALL_DEPENDENSI.bat atau install Python dari python.org
        pause
        exit /b 1
    ) else (
        set PY_CMD=python
    )
)

echo ============================================================
echo   Menjalankan artnet2WSS.py
echo   Pastikan server.py sudah berjalan terlebih dahulu.
echo ============================================================
echo.
echo [Diagnostik]
echo   Interpreter dipakai : %PY_CMD%
where %PY_CMD%
%PY_CMD% --version
echo   Folder skrip        : %cd%
echo   File yang dijalankan: %cd%\artnet2WSS.py
echo.

%PY_CMD% artnet2WSS.py

echo.
echo Aplikasi ditutup.
pause
