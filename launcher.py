"""k-on-wallpaper 启动器"""
import ctypes
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(SCRIPT_DIR, "dist", ".engine.pid")
EXE_PATH = os.path.join(SCRIPT_DIR, "dist", "k-on-wallpaper.exe")


def is_process_alive(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x0400, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


# 检查是否已在运行
if os.path.exists(PID_FILE):
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if is_process_alive(pid):
            ctypes.windll.user32.MessageBoxW(0, "应用已在运行！", "k-on-wallpaper", 48)
            sys.exit(0)
        else:
            os.remove(PID_FILE)
    except (ValueError, OSError):
        try:
            os.remove(PID_FILE)
        except OSError:
            pass

# 启动引擎
os.startfile(EXE_PATH)
