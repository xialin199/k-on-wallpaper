"""
Wallpaper Engine — Win11 桌面壁纸自动轮换引擎
入口文件

启动方式:
    py main.py                 # 前台运行，Ctrl+C 停止
    py main.py --once          # 只换一次，然后退出
    py main.py --config 自定义配置.yaml  # 指定配置文件
    start_hidden.bat           # 无窗口后台运行
    stop.bat                   # 停止后台引擎
"""
import argparse
import atexit
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 Python 路径中（支持 PyInstaller 和源码运行）
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import yaml

from engine.scheduler import WallpaperScheduler
from engine.tray import TrayIcon

# PID 文件路径（用于后台模式停止）
PID_FILE = os.path.join(SCRIPT_DIR, ".engine.pid")

# ============================================
# 日志配置
# ============================================


def setup_logging(config: dict) -> logging.Logger:
    """配置日志系统"""
    log_cfg = config.get("logging", {})
    level_name = log_cfg.get("level", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    # 日志目录
    log_dir = Path(SCRIPT_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日志文件（按天命名）
    log_file = log_dir / f"engine_{datetime.now().strftime('%Y%m%d')}.log"

    # 根 logger
    logger = logging.getLogger("engine")
    logger.setLevel(level)

    # 格式
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 handler（始终可用）
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 控制台 handler（仅当前台模式时添加，后台模式无 stdout）
    try:
        if sys.stdout and sys.stdout.isatty():
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(fmt)
            logger.addHandler(ch)
    except Exception:
        pass  # 后台模式，无控制台，只写日志文件

    return logger


def load_config(config_path: str) -> dict:
    """加载 YAML 配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def write_pid():
    """写入 PID 文件（用于 stop.bat 定位进程）"""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_pid():
    """删除 PID 文件"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError:
        pass


def is_another_instance_running() -> bool:
    """检测是否已有引擎在运行"""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        # 检查该 PID 的进程是否还存在
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
    except (ValueError, OSError):
        pass
    # PID 文件存在但进程已死 → 清理
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Win11 桌面壁纸自动轮换引擎"
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="配置文件路径（默认: 同目录的 config.yaml）",
    )
    parser.add_argument(
        "--once", "-1",
        action="store_true",
        help="只换一次壁纸，不进入循环",
    )
    args = parser.parse_args()

    # 定位配置文件
    script_dir = Path(SCRIPT_DIR)
    config_path = args.config or (script_dir / "config.yaml")

    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件不存在: {config_path}")
        sys.exit(1)

    # 加载配置 + 设置日志
    config = load_config(str(config_path))

    # 将配置中的相对路径转为绝对路径（基于 exe 所在目录）
    for cfg_path_list in [config.get("sources", {}).get("local", {}).get("directories", [])]:
        for i, p in enumerate(cfg_path_list):
            if not os.path.isabs(p):
                cfg_path_list[i] = os.path.normpath(os.path.join(SCRIPT_DIR, p))
    history_file = config.get("history", {}).get("file", "")
    if history_file and not os.path.isabs(history_file):
        config["history"]["file"] = os.path.normpath(os.path.join(SCRIPT_DIR, history_file))

    logger = setup_logging(config)
    logger.info(f"配置文件: {config_path}")

    # 创建调度器
    scheduler = WallpaperScheduler(config)
    scheduler.load_history()

    if args.once:
        if is_another_instance_running():
            logger.warning("引擎已在后台运行中，跳过单次模式（避免双引擎打架）")
            print("[SKIP] 引擎已在后台运行，不需要 --once。用 stop.bat 停止后再试。")
            sys.exit(0)
        logger.info("单次模式：更换壁纸后退出")
        success = scheduler.change_wallpaper()
        sys.exit(0 if success else 1)

    if is_another_instance_running():
        logger.error("检测到已有引擎在运行，拒绝重复启动")
        print("[ERROR] 引擎已在后台运行中。先用 stop.bat 停止，再启动。")
        sys.exit(1)

    # 写入 PID（用于后台模式 stop.bat）
    write_pid()
    atexit.register(remove_pid)
    logger.info(f"PID: {os.getpid()}")

    # ── 系统托盘 ──
    def _on_next():
        scheduler.change_wallpaper()

    def _on_toggle_pause():
        if scheduler.is_paused():
            scheduler.resume()
            tray.set_paused(False)
        else:
            scheduler.pause()
            tray.set_paused(True)

    def _on_pause_2h():
        scheduler.pause_for(2)
        tray.set_paused(True)

    def _on_open_config():
        os.startfile(str(config_path))

    def _on_exit():
        tray.stop()
        scheduler.stop()
        remove_pid()
        sys.exit(0)

    icon_path = os.path.join(SCRIPT_DIR, "图标.ico")
    tray = TrayIcon(callbacks={
        "next": _on_next,
        "toggle_pause": _on_toggle_pause,
        "pause_2h": _on_pause_2h,
        "open_config": _on_open_config,
        "exit": _on_exit,
    }, config=config, icon_path=icon_path)
    tray.start()
    logger.info("托盘已启动 — 右键状态栏图标控制引擎")

    # 注册信号处理
    def signal_handler(sig, frame):
        logger.info("收到退出信号")
        tray.stop()
        scheduler.stop()
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()
    except Exception as e:
        logger.exception(f"未预料的错误: {e}")
        scheduler.stop()
        sys.exit(1)
    finally:
        tray.stop()
        remove_pid()


if __name__ == "__main__":
    main()
