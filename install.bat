@echo off
title Wallpaper Engine - Install
cd /d D:\WallpaperEngine

echo.
echo   [Wallpaper Engine] Installing dependencies...
echo.

py -m pip install -r requirements.txt

echo.
echo   Done! Now:
echo     1. Put your wallpaper images into wallpapers\imported\
echo     2. Run: start.bat  (or: py main.py)
echo     3. Test single swap: py main.py --once
echo.
pause
