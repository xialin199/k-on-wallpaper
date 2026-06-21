"""
壁纸设置器 — 调用 Windows API 更换桌面壁纸
支持 Win11 单屏/多屏，多种填充模式
"""
import ctypes
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Win32 API 常量
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

# 壁纸样式（用于 IDesktopWallpaper 接口, Phase 2 多屏支持）
FIT_MODES = {
    "fill": 10,      # 填充（保持比例，裁切超出部分）
    "fit": 6,        # 适应（保持比例，留黑边）
    "stretch": 2,    # 拉伸（不保持比例）
    "tile": 0,       # 平铺
    "center": 1,     # 居中
    "span": 22,      # 跨区（多屏共享一张）
}


def set_wallpaper_basic(image_path: str) -> bool:
    """
    基础设置方式 — SystemParametersInfoW
    适用于所有 Windows 版本，单屏/多屏统一壁纸
    """
    if not os.path.exists(image_path):
        logger.error(f"图片不存在: {image_path}")
        return False

    abs_path = os.path.abspath(image_path)

    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        abs_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    )

    if result:
        logger.info(f"壁纸已设置: {Path(image_path).name}")
        return True
    else:
        logger.error(f"设置壁纸失败: {image_path}")
        return False


def set_wallpaper_advanced(image_path: str, fit_mode: str = "fill") -> bool:
    """
    高级设置方式 — IDesktopWallpaper COM 接口
    支持多显示器独立壁纸、精确填充模式
    需要 comtypes 包

    返回 True/False，如果 comtypes 不可用则回退到基础方式
    """
    try:
        import comtypes.client
    except ImportError:
        logger.debug("comtypes 未安装，使用基础设置方式")
        return set_wallpaper_basic(image_path)

    if not os.path.exists(image_path):
        logger.error(f"图片不存在: {image_path}")
        return False

    abs_path = os.path.abspath(image_path)
    fit_value = FIT_MODES.get(fit_mode, 10)

    try:
        # 创建 IDesktopWallpaper 实例
        wallpaper = comtypes.client.CreateObject(
            "{C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD}",
            interface="{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}",
        )

        monitor_count = wallpaper.GetMonitorDevicePathCount()

        # 尝试为每个显示器设置壁纸
        for i in range(monitor_count):
            monitor_id = wallpaper.GetMonitorDevicePathAt(i)
            wallpaper.SetWallpaper(monitor_id, abs_path)
            wallpaper.SetPosition(fit_value)

        logger.info(
            f"壁纸已设置(高级): {Path(image_path).name}, "
            f"模式={fit_mode}, 屏幕数={monitor_count}"
        )
        return True

    except Exception as e:
        logger.warning(f"高级设置失败 ({e})，回退到基础方式")
        return set_wallpaper_basic(image_path)


def set_wallpaper(image_path: str, fit_mode: str = "fill", try_advanced: bool = True) -> bool:
    """
    设置壁纸的统一入口
    - try_advanced=True: 优先使用高级接口，失败时自动回退
    - try_advanced=False: 直接用基础接口
    """
    if try_advanced:
        return set_wallpaper_advanced(image_path, fit_mode)
    return set_wallpaper_basic(image_path)
