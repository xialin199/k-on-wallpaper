# k-on-wallpaper

> Win11 桌面壁纸自动轮换引擎 — 自定义图标、系统托盘、交叉淡入淡出、零依赖便携版

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 功能

- 🖼️ **自动轮换** — 定时从本地文件夹随机换壁纸
- 🎬 **交叉淡入淡出** — PIL 图像混合，不创建覆盖窗口，不挡应用
- 📌 **系统托盘** — 右键菜单控制（下一张/暂停/打开配置/退出）
- 🚀 **开机自启** — 一键开关
- 📦 **便携免安装** — 单文件 exe，不依赖 Python
- 🎨 **自定义图标** — 托盘 + exe + 桌面快捷方式

## 快速开始

### 方式一：直接用 exe（普通用户）

1. 下载 [k-on-wallpaper.zip](https://github.com/xialin199/k-on-wallpaper/releases)
2. 解压到任意文件夹
3. 双击 `start.vbs` → 右下角出现托盘图标 → 右键控制一切
4. 把壁纸图扔进 `wallpapers/imported/`

### 方式二：从源码运行（开发者）

```bash
git clone https://github.com/xialin199/k-on-wallpaper.git
cd k-on-wallpaper
pip install -r requirements.txt
py main.py           # 前台运行
py main.py --once    # 测试单次换壁纸
```

### 构建 exe

```bash
pip install pyinstaller
py -m PyInstaller --onefile --noconsole --name "k-on-wallpaper" --icon 图标.ico --paths . --add-data "config.yaml;." main.py
```

## 项目结构

```
k-on-wallpaper/
├── main.py                 # 入口
├── config.yaml             # 配置文件
├── requirements.txt        # Python 依赖
├── launcher.py             # 启动检查器（防重复启动）
├── start.vbs               # 一键启动脚本
├── stop.bat                # 停止脚本
├── autostart.bat           # 开机自启开关
├── 图标.png / 图标.ico     # 应用图标
│
├── engine/
│   ├── scheduler.py        # 调度引擎（定时 + 转场 + 暂停）
│   ├── wallpaper_setter.py # Windows 壁纸 API（ctypes）
│   ├── local_source.py     # 本地图库扫描 + 随机选取
│   ├── history.py          # 轮换历史（避免短期重复）
│   ├── transition.py       # PIL 图像混合转场
│   └── tray.py             # 系统托盘图标 + 右键菜单
│
├── wallpapers/
│   ├── imported/           # 用户导入的壁纸
│   ├── ai_generated/       # AI 生成的壁纸
│   └── favorites/          # 收藏壁纸
│
└── dist/                   # 构建产物
    └── k-on-wallpaper.exe
```

## 技术亮点

| 模块 | 实现 |
|---|---|
| 壁纸设置 | `SystemParametersInfoW` (Win32 API via ctypes) |
| 交叉淡入淡出 | PIL `Image.blend()` 生成混合帧，逐帧设壁纸 |
| 托盘图标 | `Shell_NotifyIcon` + `CreatePopupMenu` (纯 Win32) |
| 定时调度 | 主循环 + `timedelta`，支持暂停/恢复/定时暂停 |
| 历史去重 | JSON 文件持久化，最多记录 N 张 |
| 打包 | PyInstaller onefile，所有路径相对，便携 |

**零第三方 GUI 依赖。** 全部功能用 Python 标准库 + ctypes 调用 Win32 API 实现。

## 配置文件

```yaml
# config.yaml
engine:
  rotation_interval_minutes: 5   # 换壁纸间隔

sources:
  local:
    directories:
      - "wallpapers\\imported"
      - "wallpapers\\favorites"

display:
  fit_mode: "fill"              # fill | fit | stretch | tile | center | span
  transition: "fade"            # fade | none
  transition_duration: 0.7      # 转场时长（秒）
```

## 未来计划

- [ ] 时间段智能切换（早/中/晚不同文件夹）
- [ ] Bing 每日壁纸自动下载
- [ ] 番茄钟专注模式（专注时壁纸变暗）
- [ ] 多显示器独立壁纸
- [ ] SD 本地生成集成（深夜自动生成）

## License

MIT © 2025
