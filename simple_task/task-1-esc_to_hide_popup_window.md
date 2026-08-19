---
created_at: 2026-08-19T10:43:18+08:00
status: done # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 情况描述

翻译弹窗出来后，我按esc它不消失

# 执行记录

## 调查

翻译弹窗 `PopupWindow`（main.py）的 ESC 处理：

- 事件过滤器 `self.text_edit.installEventFilter(self)` 只挂在 `text_edit` 上，而按键事件只发给**当前持有焦点的控件**。
- `_display_and_show()` 首次显示时只调用了 `show() / raise_() / activateWindow()`，**没有 `setFocus()`**。
- 于是焦点落在先创建的 🔊 发音按钮（`pronounce_btn`）上，而不是 `text_edit`。按 ESC 时事件不经过 `text_edit`，过滤器收不到；`PopupWindow` 也没有重写 `keyPressEvent`，事件冒泡到顶层也没人处理。
- 对比 `InputWindow`：它在 `_show_and_clear()` 里显式 `self.input_edit.setFocus()`，所以输入窗的 ESC 一直正常，翻译窗恰恰漏了这一步。

## 修复（main.py，两处）

1. `_display_and_show()` 首次显示时加 `self.text_edit.setFocus()`——与输入窗保持一致，保证焦点落在文本区。
2. 为 `PopupWindow` 增加 `keyPressEvent` 兜底——即使焦点在发音按钮等其它控件上，ESC 也会从未处理事件的子控件冒泡到顶层窗口，同样隐藏弹窗并 `restore_previous_window()`。

## 验证

- `uv run python -m py_compile main.py` 编译通过。
- 行为说明：弹窗显示后按 ESC 会隐藏弹窗并恢复之前聚焦的窗口；该修复同时覆盖「点过发音按钮后焦点丢失」的边缘情况。

# 人验证

esc可以顺利关闭弹窗了