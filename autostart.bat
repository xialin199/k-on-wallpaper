@echo off
title Wallpaper Engine - AutoStart
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WallpaperEngine.vbs"

if exist "%STARTUP_VBS%" (
    echo   AutoStart: ON
    echo.
    choice /c yn /n /m "  Turn OFF? [Y/N] "
    if errorlevel 2 goto done
    del /f "%STARTUP_VBS%"
    echo   AutoStart: OFF
) else (
    echo   AutoStart: OFF
    echo.
    choice /c yn /n /m "  Turn ON? [Y/N] "
    if errorlevel 2 goto done
    (
    echo Set ws = CreateObject^("Wscript.Shell"^)
    echo ws.Run "D:\WallpaperEngine\dist\k-on-wallpaper.exe", 0, False
    ) > "%STARTUP_VBS%"
    echo   AutoStart: ON
)

:done
echo.
pause
