import ctypes
import math
import time
from typing import Callable

from pynput import mouse


# 定义 Win32 API 结构体，用于获取全局光标状态
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("hCursor", ctypes.c_void_p),
        ("ptScreenPos", POINT),
    ]


# Win32 常量
IDC_IBEAM = 32513  # 文本选择光标(I形态)
CURSOR_SHOWING = 0x00000001


def is_ibeam_cursor() -> bool:
    """
    判断当前全局鼠标光标是否为 I 形态 (IDC_IBEAM)
    """
    try:
        user32 = ctypes.windll.user32

        # 获取全局光标信息
        ci = CURSORINFO()
        ci.cbSize = ctypes.sizeof(CURSORINFO)

        if user32.GetCursorInfo(ctypes.byref(ci)):
            # 确保光标是显示状态
            if ci.flags & CURSOR_SHOWING:
                # 获取系统预设的 I 形态光标句柄
                h_ibeam = user32.LoadCursorW(0, IDC_IBEAM)
                # 比较当前光标和 I 形态光标
                return ci.hCursor == h_ibeam
        return False
    except Exception:
        return False


# 鼠标事件监听器，判断双击与拖拽
class TextSelectionDetector:
    def __init__(self, on_select_callback: Callable[[str], None]):
        """
        :param on_select_callback: 当检测到文本选中时执行的函数。
                                   回调函数会接收一个字符串参数，说明触发类型 ("double_click" 或 "drag")
        """
        self.on_select_callback = on_select_callback

        # 状态记录
        self.last_click_time = 0.0
        self.drag_start_pos = None
        self.was_ibeam_on_press = False

        # 判定阈值设置
        self.double_click_threshold = 0.25  # 双击判定时间(秒)
        self.drag_distance_threshold = 10  # 拖拽判定距离(像素)，防止手抖微动

    def on_click(self, x, y, button, pressed):
        # 只处理鼠标左键
        if button != mouse.Button.left:
            return

        current_time = time.time()

        if pressed:
            # 【鼠标按下时】
            self.was_ibeam_on_press = is_ibeam_cursor()
            self.drag_start_pos = (x, y)

            # 判断条件1：在 I 形态下，且两次点击时间间隔小于双击阈值
            if self.was_ibeam_on_press:
                if current_time - self.last_click_time < self.double_click_threshold:
                    # 触发回调函数
                    if self.on_select_callback:
                        self.on_select_callback("double_click")

                    # 重置时间，防止连续三次点击触发两次双击提示
                    self.last_click_time = 0.0
                else:
                    self.last_click_time = current_time

        else:
            # 【鼠标松开时】
            # 判断条件2：按下时是 I 形态，且松开时的坐标与按下时的坐标有较大偏移
            if self.was_ibeam_on_press and self.drag_start_pos is not None:
                dx = x - self.drag_start_pos[0]
                dy = y - self.drag_start_pos[1]
                # 计算两点之间的直线距离
                distance = math.hypot(dx, dy)

                if distance > self.drag_distance_threshold:
                    # 触发回调函数
                    if self.on_select_callback:
                        self.on_select_callback(f"drag_{int(distance)}px")

            # 动作结束，清理状态
            self.drag_start_pos = None
            self.was_ibeam_on_press = False


# 提供给外部引用的工厂函数
def create_selection_listener(
    on_select_callback: Callable[[str], None],
) -> mouse.Listener:
    """
    创建一个专门用于监听文本选中的鼠标监听器。

    :param on_select_callback: 必须是一个接收一个字符串参数的函数。
                               例如: def my_callback(action_type): ...
    :return: pynput.mouse.Listener 实例
    """
    detector = TextSelectionDetector(on_select_callback)
    listener = mouse.Listener(on_click=detector.on_click)
    return listener
