---
created_at: 2026-08-19T10:49:08+08:00
status: done # done | todo
---

> 人下达task，你执行task并记录执行过程，人验收后记录验收看到的东西判断是否完成，你继续执行task，直到人认为结束了再手动修改status

# 说明

现在弹窗出现在下方，这样的话如果鼠标在下方或者右边，就会导致看不见弹窗的内容，所以应该加一个智能检测

# 执行记录

## 调查

`PopupWindow._display_and_show()` 里定位逻辑是固定 `cursor + (15, 15)`（鼠标右下方）：

```python
cursor = QCursor.pos()
self.move(cursor.x() + 15, cursor.y() + 15)
```

窗口尺寸 420x220，鼠标在屏幕右侧/底部附近时弹窗会整体或部分溢出屏幕，内容看不见。

## 方案

新增 `_move_near_cursor()` 辅助方法，在首次显示时调用：

1. 默认放到鼠标右下方（`cursor + 15`）。
2. 右/下放不下时翻转到鼠标左/上方（`cursor - w - 15`）。
3. 最后夹取（clamp）到鼠标所在屏幕的 `availableGeometry()` 内，保证完全可见（兜底，覆盖屏幕小于弹窗等极端情况）。

使用 `QApplication.screenAt(cursor)` 取鼠标所在屏幕，取不到时回退到 `primaryScreen()`；`availableGeometry()` 会自动排除任务栏区域。

## 验证

- `uv run python -m py_compile main.py` 编译通过。
- 行为说明：鼠标在屏幕右下角时弹窗会翻转到左上方显示；在其它位置仍保持右下角显示，且不会溢出屏幕。

# 人验证

在下方以及右边的时候弹窗确实可以往中间弹了