---
created_at: 2026-09-23T14:52:55+08:00
status: todo # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

- 托盘图标右键现在只有 退出 一个选项，现在加入一个 自动发音 选项
- 初始状态是翻译英文后自动发音，通过托盘点击选项后翻译后不自动发音要自己点击发音图标才发音，再点击一次就变为自动发音
- 可不可以做到如果自动发音托盘菜单就显示 “自动发音 ☑️”，点击后就变为 “自动发音” 这就是不会自动发音
- 复用已有的发音逻辑

# 执行记录

## 方案

- `tray.py`：新增 `auto_speak_toggled = pyqtSignal(bool)` 和 `auto_speak_enabled`（默认 `True`）；右键菜单在「退出」之前加入 `auto_speak_action`，文字随状态切换 `自动发音 ☑️` / `自动发音`，点击即切换并发出信号。
- `main.py`：新增模块级开关 `_auto_speak = True`；`PopupWindow.auto_speak(text)` 只是设置 `_original_text` 后调用已有的 `_pronounce()`，完全复用原发音逻辑（含 `_speaking` 防重入）。
- 发音时机：在 `on_trigger` / `on_input_submit` 里翻译结果返回并显示之后，若原文是英文且翻译成功，则 `_auto_speak` 为真时调用 `_window.auto_speak(text)`。此时翻译已显示在弹窗中，原文即朗读内容。
- 托盘信号 `auto_speak_toggled` 连到 `on_auto_speak_toggled`，更新 `_auto_speak`。

## 验证

- `uv run python -m py_compile main.py tray.py` 编译通过。
- 行为：默认勾选（自动发音）；点一次菜单变成「自动发音」，翻译后不再自动朗读，需要自己点 🔊；再点一次变回「自动发音 ☑️」，恢复自动朗读。

人工验证成功，自动发音时候可以发音，取消后就没了