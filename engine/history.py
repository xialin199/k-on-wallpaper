"""
历史记录 — 追踪已使用的壁纸，避免短期重复
"""
import json
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class RotationHistory:
    """壁纸轮换历史记录"""

    def __init__(self, filepath: str, max_size: int = 50):
        """
        Args:
            filepath: 历史记录 JSON 文件路径
            max_size: 最多保留多少条记录（避免短期重复的窗口大小）
        """
        self.filepath = Path(filepath)
        self.max_size = max_size
        self._entries: List[str] = []

    def load(self):
        """从文件加载历史记录"""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._entries = data.get("entries", [])
                logger.debug(f"已加载 {len(self._entries)} 条历史记录")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"历史记录文件损坏，重置: {e}")
                self._entries = []
        else:
            logger.info("历史记录文件不存在，从空开始")
            self._entries = []

    def save(self):
        """保存历史记录到文件"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"entries": self._entries, "max_size": self.max_size},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def add(self, image_path: str):
        """
        添加一条使用记录

        逻辑：
        1. 如果这张图已经在记录里 → 移到最前面（刷新位置）
        2. 如果是新图 → 插入最前面
        3. 超出 max_size → 删除最旧的
        """
        abs_path = os.path.abspath(image_path)

        # 移除旧位置（如果存在）
        if abs_path in self._entries:
            self._entries.remove(abs_path)

        # 插入到最前面
        self._entries.insert(0, abs_path)

        # 截断超出的部分
        if len(self._entries) > self.max_size:
            self._entries = self._entries[: self.max_size]

        self.save()

    def get_exclude_list(self) -> List[str]:
        """获取需要排除的图片列表（已在最近的轮换记录中）"""
        return list(self._entries)

    def clear(self):
        """清空历史记录"""
        self._entries = []
        self.save()
        logger.info("历史记录已清空")

    def __len__(self) -> int:
        return len(self._entries)
