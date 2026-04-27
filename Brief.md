# translator — 桌面划词翻译工具

# 环境

- OS: Windows
- Shell: Nushell (nu)

## 项目简介

Windows 桌面翻译工具，系统托盘常驻。在任何应用中选中文本后按 `Alt+A` 或点击悬浮图标，即可显示翻译结果。

依赖网易有道词典 suggest API（免费，无需 key），另有百度翻译 API demo 作为备选参考。

## 启动方式

使用 uv（推荐）：`uv run main.py`

Python 3.12，依赖见 pyproject.toml。

## 核心模块

| 模块 | 职责 |
|------|------|
| `main.py` | 入口。初始化 PyQt6 App、PopupWindow、FloatingWindow、Tray，启动 pynput 全局监听 |
| `detect_select_text.py` | 检测文本选中。通过 Win32 API 判读光标是否为 IBeam，区分双击选中 vs 拖拽选中 |
| `floating_window.py` | 选中文本后出现在光标附近的翻译小图标。点击触发翻译 |
| `translation.py` | 调用有道 suggest API 获取翻译结果，返回格式化文本 |
| `tray.py` | 系统托盘图标，提供右键退出 |

### 辅助文件

| 文件 | 用途 |
|------|------|
| `make_exe.py` | 调用 PyInstaller 打包为单文件 exe |
| `translator.spec` | PyInstaller spec 文件 |
| `dev/knowledge.md` | 开发笔记和 API 文档 |
| `dev/roadmap.md` | 开发记录和解决过的 Bug 分析 |

## 技术栈

- Python 3.12
- PyQt6 — GUI 框架
- pynput — 全局键盘/鼠标钩子（非 Qt 快捷键，保证跨应用生效）
- pyperclip — 剪贴板操作
- requests — HTTP 请求
- ctypes — Win32 API（获取光标类型判断文本选中）
- PyInstaller — 打包 exe

## 架构要点

### 线程模型

- **PyQt6 主线程**（UI 线程）：所有窗口操作必须在此线程
- **pynput 后台线程**：监听全局快捷键和鼠标
- **翻译线程**：点击悬浮窗时 `threading.Thread(target=on_trigger, daemon=True)` 将翻译任务丢到后台，避免阻塞 UI

跨线程通信全部通过 `pyqtSignal` 完成。

### 选中检测机制

见 `detect_select_text.py`:
- 双击选中：检测两次鼠标左键单击间隔 < 0.25s 且光标为 IBeam
- 拖拽选中：检测鼠标按下时是 IBeam，松开时位移 > 10px
- 使用 Win32 API `GetCursorInfo` + `LoadCursorW(IDC_IBEAM)` 判断光标类型

### 窗口行为

- **PopupWindow**：无边框、置顶、Tool 类型。首次显示定位到鼠标位置，之后只更新文本不移动
- **FloatingWindow**：无边框、不抢占焦点（`WA_ShowWithoutActivating`）确保可以复制到选中的文本。
- **保护期**：FloatingWindow 显示后 0.3s 内忽略隐藏指令（解决双击选中时 显示→隐藏 竞争）

### 翻译流程

1. 用户选中文本 → FloatingWindow 显示
2. 用户按 Alt+A 或点击 FloatingWindow
3. 模拟 Ctrl+C 复制选中文本到剪贴板
4. 读取剪贴板 → 调用 `youdao_translation()`
5. 先显示"正在翻译..." → 拿到结果后更新 PopupWindow
6. 点击窗口外部区域关闭

### 防抖

`on_trigger()` 有 0.5s 防抖，防止短时间内重复触发。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Alt+A` | 翻译选中文本 |
| `Alt+Tab` | 切换别的窗口的时候隐藏悬浮窗 |
| 鼠标点击外部 | 关闭翻译结果窗口、隐藏悬浮窗 |

## 构建

```bash
uv run make_exe.py
```

输出：`dist/translator.exe`（单文件，无控制台窗口）

## 已知

- 有道 API 首次请求较慢（服务端连接池问题），后续请求正常。若长时间不请求会再次变慢
