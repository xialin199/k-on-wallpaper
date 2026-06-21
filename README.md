# 🎬 k-on-wallpaper

<p align="center">
  <img src="图标.png" width="128" alt="k-on-wallpaper icon">
</p>

<p align="center">
  <strong>Win11 桌面壁纸自动轮换引擎</strong><br>
  系统托盘控制 · 交叉淡入淡出 · 便携免安装
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.11%2B-green?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero-lightgrey?style=flat-square" alt="Dependencies">
  <img src="https://img.shields.io/badge/build-PyInstaller-purple?style=flat-square" alt="Build">
</p>

---

## ✨ 功能

| 功能 | 说明 |
|---|---|
| 🖼️ 自动轮换 | 定时从本地文件夹随机选取壁纸，支持多目录、子文件夹递归 |
| 🎬 交叉淡入淡出 | PIL 图像混合技术——不创建覆盖窗口，不挡任何应用 |
| 📌 系统托盘 | 纯 Win32 API 实现，右键菜单全中文，实时状态提示 |
| 🚀 开机自启 | 一键开关，写入 Windows Startup 文件夹 |
| 🛡️ 防重复启动 | `OpenProcess` 验证进程死活，不会残留僵尸进程 |
| 🔄 暂停/恢复 | 玩游戏时暂停，会后自动恢复 |
| 📜 不短期重复 | JSON 历史记录，默认 50 张窗口 |
| 📦 便携免安装 | 单文件 exe，所有路径相对——U盘都能跑 |
| 🎨 自定义图标 | 托盘 + exe + 桌面快捷方式全部自定义 |

## 🚀 快速开始

### 直接下载（普通用户）

1. 从 [Releases](https://github.com/xialin199/k-on-wallpaper/releases) 下载 `k-on-wallpaper.zip`
2. 解压到任意文件夹
3. 双击 `start.vbs`
4. 右下角托盘图标出现 → 右键控制一切
5. 把壁纸图扔进 `wallpapers/imported/`

### 从源码运行

```bash
git clone https://github.com/xialin199/k-on-wallpaper.git
cd k-on-wallpaper
pip install -r requirements.txt
python main.py           # 前台运行
python main.py --once    # 测试单次换壁纸
```

### 自己构建 exe

```bash
pip install pyinstaller
py -m PyInstaller --onefile --noconsole \
  --name "k-on-wallpaper" \
  --icon 图标.ico \
  --paths . \
  --add-data "config.yaml;." \
  main.py
# 产物在 dist/k-on-wallpaper.exe
```

## 🏗️ 架构

```
main.py                         # 入口：CLI 参数、PID 管理、信号处理
├── engine/scheduler.py         # 调度引擎：定时循环、暂停/恢复、转场触发
├── engine/wallpaper_setter.py  # 壁纸 API：SystemParametersInfoW (ctypes)
├── engine/local_source.py      # 图源管理：递归扫描、随机选取、PIL 验证
├── engine/transition.py        # 转场效果：PIL Image.blend 混合帧
├── engine/tray.py              # 托盘图标：Shell_NotifyIcon + popup menu
├── engine/history.py           # 历史记录：JSON 持久化、避免短期重复
├── launcher.py                 # 启动检查器：OpenProcess 验证进程死活
├── start.vbs / stop.bat        # 一键启停脚本
└── autostart.bat               # 开机自启开关
```

## 🔧 技术栈

| 模块 | 实现 | 外部依赖 |
|---|---|---|
| 壁纸设置 | `SystemParametersInfoW` via ctypes | 0 |
| 托盘菜单 | `Shell_NotifyIcon` + `CreatePopupMenu` | 0 |
| 图像处理 | PIL `Image.blend` / `Image.resize` | Pillow |
| 图片验证 | PIL `Image.open().verify()` | Pillow |
| 配置解析 | YAML | PyYAML |
| 打包 | PyInstaller onefile | PyInstaller |
| 进程检测 | `OpenProcess` via kernel32 | 0 |
| 全栈无第三方 GUI 依赖 | — | tkinter / PyQt / etc |

## ⚙️ 配置

```yaml
# config.yaml（解压后和 exe 同目录，所有路径相对）
engine:
  rotation_interval_minutes: 5

sources:
  local:
    directories:
      - "wallpapers\\imported"
      - "wallpapers\\favorites"
    recursive: true
    extensions: [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

display:
  fit_mode: "fill"              # fill | fit | stretch | tile | center
  transition: "fade"            # fade | none
  transition_duration: 0.7

history:
  max_history: 50
```

## 🗺️ 路线图

- [ ] 时间段智能切换（早上明亮 / 晚上暗色）
- [ ] 番茄钟专注模式（专注时壁纸变暗）
- [ ] Bing / Unsplash 每日壁纸自动下载
- [ ] 多显示器独立壁纸
- [ ] SD 本地生成集成（深夜自动生成）
- [ ] 壁纸收藏夹 / 标签分类

## 📄 License

MIT © 2025

---

<p align="center">
  <sub>Built with ❤️ and Win32 API</sub>
</p>
