import ctypes

g_previous_hwnd = 0


def restore_previous_window():
    """恢复焦点到之前记录的窗口"""
    global g_previous_hwnd
    if not g_previous_hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        # 这堆注释应该不用，直接设置聚焦是可行的
        # kernel32 = ctypes.windll.kernel32
        # current_tid = kernel32.GetCurrentThreadId()
        # target_tid = user32.GetWindowThreadProcessId(g_previous_hwnd, None)
        # user32.AttachThreadInput(current_tid, target_tid, True)
        # user32.ShowWindow(g_previous_hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(g_previous_hwnd)
        # user32.AttachThreadInput(current_tid, target_tid, False)
    except Exception as e:
        print(f"恢复窗口焦点失败: {e}")
    finally:
        g_previous_hwnd = 0
