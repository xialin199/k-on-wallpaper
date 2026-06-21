"""
本地图源 — 扫描文件夹，随机选取图片
"""
import logging
import os
import random
from pathlib import Path
from typing import List, Optional

from PIL import Image

logger = logging.getLogger(__name__)

# 有效的图片魔数（文件头）
VALID_HEADERS = {
    b"\xff\xd8\xff": ".jpg",       # JPEG
    b"\x89PNG\r\n\x1a\n": ".png",  # PNG
    b"BM": ".bmp",                  # BMP
    b"RIFF": ".webp",              # WEBP (需进一步检查)
    b"MM\x00*": ".tiff",           # TIFF Big-endian
    b"II*\x00": ".tiff",           # TIFF Little-endian
}


def scan_directories(
    directories: List[str],
    extensions: Optional[List[str]] = None,
    recursive: bool = True,
) -> List[str]:
    """
    扫描指定目录中的图片文件

    Args:
        directories: 要扫描的目录路径列表
        extensions: 允许的扩展名（如 ['.jpg', '.png']），None=全部
        recursive: 是否递归扫描子文件夹

    Returns:
        所有找到的图片文件绝对路径列表
    """
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"]

    extensions_lower = {ext.lower() for ext in extensions}
    image_files: List[str] = []

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"目录不存在，跳过: {directory}")
            continue

        if not dir_path.is_dir():
            logger.warning(f"路径不是目录，跳过: {directory}")
            continue

        if recursive:
            for root, _, files in os.walk(directory):
                for filename in files:
                    ext = Path(filename).suffix.lower()
                    if ext in extensions_lower:
                        image_files.append(os.path.join(root, filename))
        else:
            for item in dir_path.iterdir():
                if item.is_file() and item.suffix.lower() in extensions_lower:
                    image_files.append(str(item))

    logger.debug(f"扫描完成: 找到 {len(image_files)} 张图片")
    return image_files


def validate_image(filepath: str) -> bool:
    """
    验证文件是否为有效图片（两步：扩展名 + PIL 能打开）

    Returns:
        True=有效图片, False=损坏或不支持的格式
    """
    try:
        img = Image.open(filepath)
        img.verify()  # 验证图片完整性（不加载到内存）
        return True
    except Exception:
        # verify() 可能对某些格式很严格，再试一次直接加载
        try:
            img = Image.open(filepath)
            img.load()
            return True
        except Exception as e:
            logger.debug(f"图片验证失败: {Path(filepath).name} - {e}")
            return False


def pick_random_image(
    directories: List[str],
    extensions: Optional[List[str]] = None,
    recursive: bool = True,
    exclude: Optional[List[str]] = None,
    validate: bool = True,
) -> Optional[str]:
    """
    从指定目录中随机挑选一张有效图片

    Args:
        directories: 目录列表
        extensions: 允许的扩展名
        recursive: 是否递归
        exclude: 要排除的图片路径列表（历史记录）
        validate: 是否验证图片有效性

    Returns:
        图片绝对路径，如果没有可用图片则返回 None
    """
    exclude_set = set(exclude or [])

    # 扫描所有图片
    all_images = scan_directories(directories, extensions, recursive)

    if not all_images:
        logger.warning("没有找到任何图片文件")
        return None

    # 排除历史记录
    available = [img for img in all_images if img not in exclude_set]

    if not available:
        logger.info("所有图片都在历史记录中，从全部图片中随机选择")
        available = all_images

    # 随机选一张并验证
    random.shuffle(available)

    for image_path in available:
        if not validate:
            return image_path

        if validate_image(image_path):
            return image_path
        else:
            logger.debug(f"跳过无效图片: {Path(image_path).name}")

    logger.warning("没有找到有效图片")
    return None
