"""
系统托盘图标 + 右键菜单
纯 Win32 API（ctypes），零额外依赖

右键菜单：
  下一张       → 立即换壁纸
  暂停/继续    → 暂停或恢复定时轮换
  暂停 2 小时  → 临时暂停
  打开配置     → 用记事本打开 config.yaml
  退出         → 停止引擎
"""
import ctypes
import logging
import os
import subprocess
import threading
from ctypes import wintypes

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

# ── 常量 ──
WM_USER = 0x0400
WM_TRAY = WM_USER + 1
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111

NIM_ADD = 0
NIM_DELETE = 2
NIM_MODIFY = 1
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
NIF_INFO = 0x10

LR_LOADFROMFILE = 0x0010
IMAGE_ICON = 1

IDI_APPLICATION = 32512

# 菜单 ID
ID_NEXT = 1001
ID_PAUSE = 1002
ID_PAUSE_2H = 1003
ID_OPEN_CONFIG = 1004
ID_EXIT = 1005


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


_wnd_proc_type = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM,
)

class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", _wnd_proc_type),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HANDLE),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


# ── API 签名 ──
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(_WNDCLASSW)]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HANDLE, wintypes.HINSTANCE, wintypes.LPVOID,
]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DestroyWindow.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.GetMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_longlong
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.LoadIconW.restype = wintypes.HICON
# 不设 argtypes —— 第二个参数可能是字符串或 MAKEINTRESOURCE(int)
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.CreatePopupMenu.argtypes = []
user32.DestroyMenu.restype = wintypes.BOOL
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.AppendMenuW.restype = wintypes.BOOL
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_ulonglong, wintypes.LPCWSTR]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.TrackPopupMenu.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]

MF_STRING = 0
MF_SEPARATOR = 0x800
TPM_RIGHTBUTTON = 2


class TrayIcon:
    """系统托盘图标管理器"""

    def __init__(self, callbacks: dict, config: dict, icon_path: str = None):
        """
        callbacks:
            'next'          → 立即换下一张
            'toggle_pause'  → 暂停/继续
            'pause_2h'      → 暂停2小时
            'open_config'   → 打开配置文件
            'exit'          → 退出引擎
        icon_path: .ico 文件路径（None=系统默认图标）
        """
        self.callbacks = callbacks
        self.config = config
        self.icon_path = icon_path
        self._hwnd = None
        self._nid = None
        self._running = False
        self._paused = False

    def start(self):
        """启动托盘图标（在独立线程中运行消息循环）"""
        self._running = True
        t = threading.Thread(target=self._message_loop, daemon=True)
        t.start()
        logger.info("托盘图标已启动")

    def stop(self):
        """停止托盘图标"""
        self._running = False
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_DESTROY, 0, 0)

    def set_paused(self, paused: bool):
        """更新暂停状态（影响菜单文字）"""
        self._paused = paused
        self._update_tooltip()

    # ── 内部 ──

    def _update_tooltip(self):
        if not self._nid:
            return
        status = "Paused" if self._paused else "Running"
        interval = self.config.get("engine", {}).get("rotation_interval_minutes", 1)
        tip = f"k-on-wallpaper ({status}, {interval}min)"
        self._nid.szTip = tip
        self._nid.uFlags = NIF_TIP
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))

    def _show_menu(self):
        """显示右键菜单"""
        menu = user32.CreatePopupMenu()

        user32.AppendMenuW(menu, MF_STRING, ID_NEXT, "下一张")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, "")
        lbl = "继续" if self._paused else "暂停"
        user32.AppendMenuW(menu, MF_STRING, ID_PAUSE, lbl)
        user32.AppendMenuW(menu, MF_STRING, ID_PAUSE_2H, "暂停 2 小时")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, "")
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN_CONFIG, "打开配置")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, "")
        user32.AppendMenuW(menu, MF_STRING, ID_EXIT, "退出")

        # 获取鼠标位置
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        user32.SetForegroundWindow(self._hwnd)
        user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, self._hwnd, None)
        user32.DestroyMenu(menu)

    def _on_command(self, cmd_id: int):
        if cmd_id == ID_NEXT:
            self.callbacks.get("next", lambda: None)()
        elif cmd_id == ID_PAUSE:
            self.callbacks.get("toggle_pause", lambda: None)()
        elif cmd_id == ID_PAUSE_2H:
            self.callbacks.get("pause_2h", lambda: None)()
        elif cmd_id == ID_OPEN_CONFIG:
            self.callbacks.get("open_config", lambda: None)()
        elif cmd_id == ID_EXIT:
            self.callbacks.get("exit", lambda: None)()

    def _message_loop(self):
        """托盘消息循环（独立线程）"""
        hinst = kernel32.GetModuleHandleW(None)

        # 注册窗口类
        wc = _WNDCLASSW()
        wc.lpfnWndProc = _wnd_proc_type(self._window_proc)
        wc.hInstance = hinst
        wc.lpszClassName = "WpEngineTray"
        user32.RegisterClassW(ctypes.byref(wc))

        # 创建隐藏窗口
        self._hwnd = user32.CreateWindowExW(
            0, "WpEngineTray", "WpEngineTray",
            0, 0, 0, 0, 0, None, None, hinst, None,
        )

        if not self._hwnd:
            logger.error("托盘窗口创建失败")
            return

        # 创建托盘图标
        self._nid = NOTIFYICONDATAW()
        self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self._nid.hWnd = self._hwnd
        self._nid.uID = 1
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self._nid.uCallbackMessage = WM_TRAY
        if self.icon_path and os.path.exists(self.icon_path):
            self._nid.hIcon = user32.LoadImageW(None, self.icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        else:
            self._nid.hIcon = user32.LoadIconW(None, IDI_APPLICATION)
        self._nid.szTip = "k-on-wallpaper"

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))

        # 消息循环
        msg = wintypes.MSG()
        while self._running:
            if user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        # 清理
        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
        logger.info("托盘图标已停止")

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam == 0x0205:  # WM_RBUTTONUP
                self._show_menu()
            return 0
        if msg == WM_COMMAND:
            self._on_command(wparam)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
