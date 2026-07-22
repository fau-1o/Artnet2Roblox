@echo off
chcp 65001 >nul
title Art-Net Bridge Server
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
echo   Menjalankan server.py
echo   Jendela ini HARUS tetap terbuka selama bermain di Roblox.
echo ============================================================
echo.

%PY_CMD% server.py

echo.
echo Server berhenti / tertutup.
pause
