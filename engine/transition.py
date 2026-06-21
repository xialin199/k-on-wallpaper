"""
壁纸切换转场 — 单帧混合过渡

方案：不创建任何覆盖窗口。
  1. PIL 将新旧壁纸 50:50 混合为一张过渡图
  2. 设过渡图为壁纸
  3. 短暂延迟后设最终新壁纸

零窗口 = 绝对不覆盖任何应用和图标。
"""
import ctypes
import logging
import os
import time

logger = logging.getLogger(__name__)

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


def _set_wp(path: str):
    """设置桌面壁纸"""
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, os.path.abspath(path),
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    )


def crossfade_wallpapers(
    old_path: str,
    new_path: str,
    duration: float = 0.6,
    frames: int = 1,
) -> bool:
    """
    单帧混合过渡：生成一张 50% 混合图 → 设为壁纸 → 延迟 → 设最终新壁纸。

    不创建窗口，不覆盖任何应用。
    """
    from PIL import Image

    if not os.path.exists(old_path) or not os.path.exists(new_path):
        return False

    try:
        old = Image.open(old_path).convert("RGB")
        new = Image.open(new_path).convert("RGB")
    except Exception as e:
        logger.warning(f"图片加载失败: {e}")
        return False

    # 缩小到处理尺寸
    mw, mh = 1280, 800
    ow, oh = old.size
    nw, nh = new.size
    tw, th = max(ow, nw), max(oh, nh)
    if tw > mw or th > mh:
        s = min(mw / tw, mh / th)
        tw, th = int(tw * s), int(th * s)

    old = old.resize((tw, th), Image.LANCZOS)
    new = new.resize((tw, th), Image.LANCZOS)

    tmp = os.path.join(os.path.dirname(new_path), "._xfade_tmp.bmp")

    try:
        # 单帧混合
        blended = Image.blend(old, new, 0.5)
        blended.save(tmp, "BMP")
        _set_wp(tmp)

        time.sleep(duration)

        # 最终新壁纸
        _set_wp(new_path)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    return True
