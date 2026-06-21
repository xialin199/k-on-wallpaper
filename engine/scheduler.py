"""
调度器 — 定时触发壁纸轮换的主循环
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from engine.wallpaper_setter import set_wallpaper
from engine.local_source import pick_random_image
from engine.history import RotationHistory
from engine.transition import crossfade_wallpapers

logger = logging.getLogger(__name__)


class WallpaperScheduler:
    """壁纸轮换调度器"""

    def __init__(self, config: dict):
        self.config = config

        engine_cfg = config.get("engine", {})
        self.interval_minutes = engine_cfg.get("rotation_interval_minutes", 30)
        self.interval_seconds = self.interval_minutes * 60

        source_cfg = config.get("sources", {}).get("local", {})
        self.directories = source_cfg.get("directories", [])
        self.recursive = source_cfg.get("recursive", True)
        self.extensions = source_cfg.get("extensions", [".jpg", ".png", ".bmp"])

        display_cfg = config.get("display", {})
        self.fit_mode = display_cfg.get("fit_mode", "fill")
        self.transition = display_cfg.get("transition", "none")
        self.transition_duration = float(display_cfg.get("transition_duration", 0.7))

        history_cfg = config.get("history", {})
        self.history = RotationHistory(
            filepath=history_cfg.get("file", "logs/history.json"),
            max_size=history_cfg.get("max_history", 50),
        )

        self._running = False
        self._next_run: Optional[datetime] = None
        self._change_count = 0
        self._current_wallpaper: Optional[str] = None
        self._paused = False
        self._pause_until: Optional[datetime] = None

    def load_history(self):
        """加载轮换历史（启动时调用）"""
        self.history.load()
        # 从历史记录推断当前壁纸
        entries = self.history.get_exclude_list()
        if entries:
            self._current_wallpaper = entries[0]

    def change_wallpaper(self) -> bool:
        """执行一次壁纸更换"""
        old_path = self._current_wallpaper

        exclude_list = self.history.get_exclude_list()
        image_path = pick_random_image(
            directories=self.directories,
            extensions=self.extensions,
            recursive=self.recursive,
            exclude=exclude_list,
            validate=True,
        )

        if image_path is None:
            logger.warning("没有找到可用图片，无法更换壁纸")
            return False

        # ── 转场：PIL 图像混合 → 逐帧设壁纸（零覆盖窗口） ──
        if self.transition == "fade" and old_path and old_path != image_path:
            logger.info(f"交叉淡入淡出 ({self.transition_duration}s)...")
            crossfade_wallpapers(old_path, image_path, self.transition_duration)
            logger.info(f"转场完成 → {image_path}")
            success = True
        else:
            success = set_wallpaper(
                image_path=image_path,
                fit_mode=self.fit_mode,
                try_advanced=False,
            )

        # ── 记录 ──
        self._current_wallpaper = image_path
        self.history.add(image_path)
        self._change_count += 1
        logger.info(
            f"第 {self._change_count} 次更换 | "
            f"下次更换: {self._next_run.strftime('%H:%M:%S') if self._next_run else 'N/A'}"
        )
        return True

    def run(self):
        """启动调度器主循环"""
        logger.info("=" * 50)
        logger.info("Wallpaper Engine 启动")
        logger.info(f"  轮换间隔: {self.interval_minutes} 分钟")
        logger.info(f"  图片目录: {len(self.directories)} 个")
        for d in self.directories:
            logger.info(f"    - {d}")
        logger.info(f"  填充模式: {self.fit_mode}")
        logger.info(f"  转场效果: {self.transition} ({self.transition_duration}s)")
        logger.info("=" * 50)

        self._running = True

        # 首次更换（无旧图，直接设置）
        logger.info("首次更换壁纸...")
        image_path = pick_random_image(
            directories=self.directories,
            extensions=self.extensions,
            recursive=self.recursive,
            validate=True,
        )
        if image_path:
            set_wallpaper(image_path, self.fit_mode, try_advanced=False)
            self._current_wallpaper = image_path
            self.history.add(image_path)
            self._change_count = 1
            logger.info(f"壁纸已设置: {image_path}")

        self._next_run = datetime.now() + timedelta(seconds=self.interval_seconds)

        while self._running:
            now = datetime.now()

            # 处理定时暂停到期
            if self._paused and self._pause_until and now >= self._pause_until:
                self.resume()

            if not self._paused and now >= self._next_run:
                self.change_wallpaper()
                self._next_run = now + timedelta(seconds=self.interval_seconds)
            time.sleep(1)

    def pause(self):
        """暂停轮换"""
        self._paused = True
        logger.info("轮换已暂停")

    def resume(self):
        """恢复轮换"""
        self._paused = False
        self._pause_until = None
        self._next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
        logger.info(f"轮换已恢复，下次: {self._next_run.strftime('%H:%M:%S')}")

    def pause_for(self, hours: int):
        """暂停指定小时数"""
        self._paused = True
        self._pause_until = datetime.now() + timedelta(hours=hours)
        logger.info(f"轮换已暂停 {hours} 小时，{self._pause_until.strftime('%H:%M:%S')} 后自动恢复")

    def is_paused(self) -> bool:
        return self._paused

    def stop(self):
        """停止调度器"""
        logger.info("正在停止 Wallpaper Engine...")
        self._running = False
        logger.info(f"已停止。共更换 {self._change_count} 次壁纸。")

    def status(self) -> dict:
        return {
            "running": self._running,
            "change_count": self._change_count,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "interval_minutes": self.interval_minutes,
            "history_size": len(self.history),
        }
