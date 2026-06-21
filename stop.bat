@echo off
cd /d D:\WallpaperEngine

echo   [k-on-wallpaper] Stopping...

if exist "dist\.engine.pid" (
    set /p PID=<"dist\.engine.pid"
    taskkill /f /pid %PID% 2>nul
    del /f "dist\.engine.pid" 2>nul
    echo   Stopped (PID %PID%).
) else (
    echo   PID file not found. Trying fallback...
    taskkill /f /im k-on-wallpaper.exe 2>nul
)

timeout /t 2 >nul
