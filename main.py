# main.py
import ctypes
import re
import sys
import threading
import time
import pyttsx3

import pyperclip
from pynput import keyboard, mouse
from pynput.keyboard import Controller, GlobalHotKeys
from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from detect_select_text import create_selection_listener, is_ibeam_cursor
from flash_card_window import FlashCardWindow
from floating_window import FloatingWindow
from read_mode_indicator import ReadModeIndicator
import global_variant
from global_variant import restore_previous_window
from translation import youdao_translation
from tray import TranslatorTray
from word_store import add_word, flush

kb = Controller()
_window = None
_floating_window = None
_flash_card_window = None

_last_trigger_time = 0.0
DEBOUNCE_SECONDS = 0.5

_auto_speak = True  # 翻译英文后是否自动发音（托盘菜单可切换）
_read_mode = False
_read_press_pos = None
_read_press_ibeam = False
_read_injecting = threading.Event()
_read_click_lock = threading.Lock()
_tray = None
_popup_hwnd = None
_read_indicator = None


class PopupWindow(QWidget):
    update_text_signal = pyqtSignal(str, str)  # original_text, translated_text
    check_click_signal = pyqtSignal()
    show_input_signal = pyqtSignal()
    show_translation_signal = pyqtSignal(str)
    check_key_signal = pyqtSignal()
    submit_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("popupWindow")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.resize(420, 220)
        self._original_text = ""
        self._speaking = False

        # ---- 整体窗口样式（仅作用于 PopupWindow 自身） ----
        self.setStyleSheet("""
            QWidget#popupWindow {
                background-color: rgba(250, 250, 250, 0.98);
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Header ----
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: transparent;
                border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.pronounce_btn = QPushButton("🔊")
        self.pronounce_btn.setFixedSize(32, 32)
        self.pronounce_btn.setToolTip("发音")
        self.pronounce_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.04);
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.08);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 0.12);
            }
        """)
        self.pronounce_btn.clicked.connect(self._pronounce)
        self.pronounce_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header_layout.addWidget(self.pronounce_btn)
        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText("输入中文或英文，按 Enter 翻译…")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                color: #1f1f1f;
                background: white;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #0078d7; }
        """)
        self.input_edit.returnPressed.connect(self._on_submit)
        header_layout.addWidget(self.input_edit, 1)

        layout.addWidget(header)

        # ---- 翻译结果显示 ----
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #1f1f1f;
                border: none;
                padding: 18px;
                font-size: 15px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.text_edit)

        self.input_edit.installEventFilter(self)
        self.text_edit.installEventFilter(self)

        # Read mode 下翻译结果显示 4 秒后自动隐藏
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(4000)
        self._auto_hide_timer.timeout.connect(self._auto_hide)

        self.update_text_signal.connect(self._display_result)
        self.check_click_signal.connect(self._handle_global_click)
        self.show_input_signal.connect(self._show_input)
        self.show_translation_signal.connect(self._show_translation)
        self.check_key_signal.connect(self._handle_global_key)

    def _dismiss(self):
        self._auto_hide_timer.stop()
        self.hide()
        restore_previous_window()

    def _auto_hide(self):
        """Read mode 的翻译结果已展示满 4 秒：用户没有在输入框里操作就隐藏。"""
        if self.isVisible() and not self.input_edit.hasFocus():
            self.hide()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape or not self.input_edit.hasFocus():
                self._dismiss()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape or not self.input_edit.hasFocus():
            self._dismiss()
            return
        super().keyPressEvent(event)

    def _handle_global_key(self):
        if self.isVisible() and not self.input_edit.hasFocus():
            self._dismiss()

    def _show_window(self):
        current_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if current_hwnd != int(self.winId()):
            global_variant.g_previous_hwnd = current_hwnd
        if not self.isVisible():
            self._move_near_cursor()
        self.show()
        self.raise_()
        self.activateWindow()

    def _show_input(self):
        self._auto_hide_timer.stop()
        self._original_text = ""
        self.input_edit.clear()
        self.text_edit.clear()
        self._show_window()
        self.input_edit.setFocus()

    def _show_translation(self, text):
        self._auto_hide_timer.stop()
        self._original_text = text
        self.input_edit.setText(text)
        self.text_edit.setPlainText("请求翻译中...")
        self._show_window()
        self.text_edit.setFocus()

    def _on_submit(self):
        text = self.input_edit.text().strip()
        if text:
            self._original_text = text
            self.text_edit.setPlainText("请求翻译中...")
            self.submit_signal.emit(text)

    def _display_result(self, original_text, translated_text):
        # 结果只更新当前查询，不重新打开已隐藏的窗口或抢走输入焦点。
        if original_text == self._original_text:
            self.text_edit.setPlainText(translated_text)
            # Read mode 下结果展示 4 秒后自动隐藏
            if _read_mode:
                self._auto_hide_timer.start()

    def _move_near_cursor(self):
        """把弹窗放到鼠标右下方；超出屏幕时翻转到鼠标左/上方，再夹取到屏幕可用区域内"""
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor)
        if screen is None:
            screen = QApplication.primaryScreen()
        area = screen.availableGeometry()

        offset = 15
        w, h = self.width(), self.height()

        # 默认放到鼠标右下方
        x = cursor.x() + offset
        y = cursor.y() + offset

        # 右/下放不下就翻转到左/上方
        if x + w > area.right():
            x = cursor.x() - w - offset
        if y + h > area.bottom():
            y = cursor.y() - h - offset

        # 兜底：夹取到可用屏幕范围内，保证完全可见
        x = max(area.left(), min(x, area.right() - w))
        y = max(area.top(), min(y, area.bottom() - h))

        self.move(x, y)

    def _handle_global_click(self):
        if self.isVisible():
            pos = QCursor.pos()
            if not self.frameGeometry().contains(pos):
                self.hide()

    def _pronounce(self):
        """在子线程中发音，避免阻塞 UI；正在发音时忽略重复点击"""
        if self._original_text and not self._speaking:
            self._speaking = True
            threading.Thread(
                target=self._speak, args=(self._original_text,), daemon=True
            ).start()

    def _speak(self, text: str):
        try:
            engine = pyttsx3.init()
            language_tokens = ("english", "en-", "en_", "409", "809") if _is_english(text) else (
                "chinese", "mandarin", "zh", "804", "0804"
            )
            for voice in engine.getProperty("voices"):
                description = f"{voice.id} {voice.name} {voice.languages}".lower()
                if any(token in description for token in language_tokens):
                    engine.setProperty("voice", voice.id)
                    break
            engine.say(text)
            engine.runAndWait()
        finally:
            self._speaking = False

    def auto_speak(self, text: str):
        """翻译完成后自动发音，复用 _pronounce 的发音逻辑"""
        if not self._speaking:
            self._speaking = True
            threading.Thread(target=self._speak, args=(text,), daemon=True).start()


def get_selected_text() -> str:
    # 有时候会单单点击 a 就翻译，估计是这里的问题，因为不是用真正的系统级别热键
    # kb.release(keyboard.Key.alt)
    # kb.release("a")
    time.sleep(0.1)

    original = pyperclip.paste()
    pyperclip.copy("")

    with kb.pressed(keyboard.Key.ctrl):
        kb.press("c")
        time.sleep(0.05)
        kb.release("c")

    time.sleep(0.05)

    text = pyperclip.paste().strip()

    pyperclip.copy(original)
    return text


def _is_english(text: str) -> bool:
    # 允许：英文字母、数字、空格、常用标点
    # ^[ -~]+$ 匹配 ASCII 32 到 126 的所有可打印字符
    return bool(re.match(r'^[a-zA-Z0-9\s\.,!?"\'-]+$', text))


def _is_successful_result(result: str) -> bool:
    """Return True if the translation result is a real result (not an error)."""
    return not result.startswith("error:")


def on_trigger():
    global _last_trigger_time
    now = time.time()
    if now - _last_trigger_time < DEBOUNCE_SECONDS:
        return
    if _floating_window is not None:
        _floating_window.hide_signal.emit()

    print("triggered")
    text = get_selected_text()
    print(f"text: {text}")

    if _window is None:
        return
    if not text:
        _window.show_input_signal.emit()
        return
    _window.show_translation_signal.emit(text)
    on_input_submit(text)


def on_input_submit(text: str):
    if not text or _window is None:
        return
    result = youdao_translation(text)
    _window.update_text_signal.emit(text, result)

    # Store English word lookups
    if _is_english(text) and _is_successful_result(result):
        add_word(text, result)
        if _auto_speak:
            _window.auto_speak(text)



def on_auto_speak_toggled(enabled: bool):
    global _auto_speak
    _auto_speak = enabled


def on_read_mode_toggled(enabled: bool):
    global _read_mode
    _read_mode = enabled
    if _read_indicator is not None:
        _read_indicator.set_enabled(enabled)
    if enabled and _floating_window is not None:
        _floating_window.hide_signal.emit()


def _translate_read_click():
    # 避免两次快速点击导致模拟点击与复制选区互相干扰。
    if not _read_click_lock.acquire(blocking=False):
        return
    try:
        if not _read_mode:
            return
        time.sleep(0.05)  # 等原始单击的松开事件传到目标程序。
        if not _read_mode:
            return
        _read_injecting.set()
        try:
            mouse.Controller().click(mouse.Button.left)
            time.sleep(0.1)  # 等监听器处理完模拟事件，再恢复真实点击检测。
        finally:
            _read_injecting.clear()
        text = get_selected_text()
        if text and _read_mode and _window is not None:
            _window.show_translation_signal.emit(text)
            on_input_submit(text)
    finally:
        _read_click_lock.release()


def on_show_translation_window():
    if _window is not None:
        _window.show_input_signal.emit()


def on_mouse_click(x, y, button, pressed):
    global _read_press_pos, _read_press_ibeam
    if _read_injecting.is_set():
        return

    if _read_mode and button == mouse.Button.left:
        if pressed:
            _read_press_pos = (x, y)
            rect = (ctypes.c_long * 4)()
            popup_at_click = (
                ctypes.windll.user32.IsWindowVisible(_popup_hwnd)
                and ctypes.windll.user32.GetWindowRect(_popup_hwnd, ctypes.byref(rect))
                and rect[0] <= x < rect[2] and rect[1] <= y < rect[3]
            )
            _read_press_ibeam = is_ibeam_cursor() and not popup_at_click
        else:
            if (_read_press_ibeam and _read_press_pos is not None
                    and abs(x - _read_press_pos[0]) < 10
                    and abs(y - _read_press_pos[1]) < 10):
                threading.Thread(target=_translate_read_click, daemon=True).start()
            _read_press_pos = None
            _read_press_ibeam = False

    if not pressed:
        return

    if _floating_window is not None:
        _floating_window.check_click_signal.emit()

    if _window is not None:
        _window.check_click_signal.emit()


def on_select_text(action_type):
    global _floating_window
    if _read_mode:
        return
    print(f"[{time.strftime('%H:%M:%S')}] 文本被选中了！触发方式: {action_type}")

    # 只要实例存在就发送信号
    if _floating_window is not None:
        print("floating 信号已发送")
        _floating_window.show_signal.emit()


def on_any_key(key):
    """隐藏悬浮图标；翻译窗口未聚焦输入框时也隐藏。"""
    if _floating_window is not None:
        _floating_window.hide_signal.emit()

    if _window is not None:
        _window.check_key_signal.emit()


def start_listeners():
    kb_listener = GlobalHotKeys(
        {
            "<alt>+q": on_show_translation_window,
            "<alt>+a": on_trigger,
            "<ctrl>+<alt>+t": lambda: _tray.toggle_read_mode_requested.emit(),
        }
    )
    kb_listener.daemon = True
    kb_listener.start()

    # 单独的监听器：任意键按下时隐藏悬浮窗
    any_key_listener = keyboard.Listener(on_press=on_any_key)
    any_key_listener.daemon = True
    any_key_listener.start()

    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    mouse_listener.daemon = True
    mouse_listener.start()

    select_text_listener = create_selection_listener(on_select_text)
    select_text_listener.daemon = True
    select_text_listener.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 确保即使所有窗口(Popup)被隐藏，程序也不会自动退出这样程序才能真正在后台运行，必须通过托盘右键退出
    app.setQuitOnLastWindowClosed(False)

    # 初始化弹出窗口
    _window = PopupWindow()
    _popup_hwnd = int(_window.winId())
    _read_indicator = ReadModeIndicator()

    # 初始化小图标
    _floating_window = FloatingWindow()
    _floating_window.clicked.connect(
        lambda: threading.Thread(target=on_trigger, daemon=True).start()
    )

    # 输入和结果共用翻译窗口，网络请求在后台线程执行。
    _window.submit_signal.connect(
        lambda text: threading.Thread(
            target=on_input_submit, args=(text,), daemon=True
        ).start()
    )

    # 初始化闪卡窗口（左键托盘弹出）
    _flash_card_window = FlashCardWindow()

    # 初始化系统托盘
    _tray = TranslatorTray()
    _tray.left_clicked.connect(_flash_card_window.show_signal.emit)
    _tray.auto_speak_toggled.connect(on_auto_speak_toggled)
    _tray.read_mode_toggled.connect(on_read_mode_toggled)
    _tray.show()

    # 启动快捷键和鼠标监听（它们是 daemon 线程，随主程序退出而停止）
    start_listeners()

    # Flush remaining word store entries when the app quits
    app.aboutToQuit.connect(flush)

    sys.exit(app.exec())
