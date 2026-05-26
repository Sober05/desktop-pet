"""Chat bubble dialog for the desktop pet."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QTextEdit, QLineEdit, QPushButton, QLabel)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QEvent, QRect
from PyQt5.QtGui import QFont, QMouseEvent

import threading
import json
from pathlib import Path
from html import escape as html_escape

CHAT_LOG_PATH = Path(__file__).parent / "chat-history.json"
MAX_CHAT_HISTORY = 50  # max messages to persist

CHAT_STYLE = """
QWidget#ChatBubble {
    background: #1e1e2e;
    border: 2px solid #FF8C42;
    border-radius: 12px;
}
QTextEdit#ChatHistory {
    background: #2a2a3c;
    color: #e0e0e0;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    padding: 6px;
    selection-background-color: #FF8C42;
}
QLineEdit#ChatInput {
    background: #2a2a3c;
    color: #ffffff;
    border: 1px solid #FF8C42;
    border-radius: 6px;
    font-size: 13px;
    padding: 4px 8px;
}
QPushButton#SendBtn {
    background: #FF8C42;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: bold;
}
QPushButton#SendBtn:hover { background: #e67a30; }
QPushButton#SendBtn:pressed { background: #cc6a20; }
"""


class ChatBubble(QWidget):
    closed = pyqtSignal()
    _result_signal = pyqtSignal(str)
    _error_signal = pyqtSignal(str)

    def __init__(self, parent=None, ai_client=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.ai = ai_client
        self._history = []
        self._streaming = False

        self._result_signal.connect(self._on_result)
        self._error_signal.connect(self._on_error)

        self._setup_ui()
        self._load_history()
        self.resize(320, 360)

    def _setup_ui(self):
        self.setObjectName("ChatBubble")
        self.setStyleSheet(CHAT_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title bar with close button
        title_row = QHBoxLayout()
        title = QLabel("  🐱 桌面宠物")
        title.setStyleSheet("color: #FF8C42; font-weight: bold; font-size: 14px;")
        title_row.addWidget(title)
        title_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #999; border: none;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { color: #FF8C42; background: #3a3a4c; border-radius: 4px; }
        """)
        close_btn.clicked.connect(self._dismiss)
        title_row.addWidget(close_btn)
        layout.addLayout(title_row)

        self.history_view = QTextEdit()
        self.history_view.setObjectName("ChatHistory")
        self.history_view.setReadOnly(True)
        self.history_view.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.history_view)

        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setObjectName("ChatInput")
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setFont(QFont("Microsoft YaHei", 10))
        self.input_box.returnPressed.connect(self._send_message)

        send_btn = QPushButton("发送")
        send_btn.setObjectName("SendBtn")
        send_btn.clicked.connect(self._send_message)

        input_row.addWidget(self.input_box)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

    def _load_history(self):
        try:
            if CHAT_LOG_PATH.exists():
                msgs = json.loads(CHAT_LOG_PATH.read_text(encoding="utf-8"))
                for m in msgs[-MAX_CHAT_HISTORY:]:
                    role = m.get("role", "")
                    content = m.get("content", "")
                    if role == "user":
                        self._append_text("你", "#88ccff", content)
                        self._history.append(m)
                    elif role == "assistant":
                        self._append_text("🐱 宠物", "#FF8C42", content)
                        self._history.append(m)
        except Exception:
            pass

    def _save_history(self):
        try:
            data = self._history[-MAX_CHAT_HISTORY:]
            CHAT_LOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        except Exception:
            pass

    def position_near(self, pet_geometry):
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()

        px = pet_geometry.center().x()
        py = pet_geometry.center().y()

        # Try right side first, then left, then top, then bottom
        positions = [
            (pet_geometry.right() + 8, py - self.height() // 2),   # right
            (pet_geometry.left() - self.width() - 8, py - self.height() // 2),  # left
            (px - self.width() // 2, pet_geometry.top() - self.height() - 8),   # top
            (px - self.width() // 2, pet_geometry.bottom() + 8),   # bottom
        ]

        for x, y in positions:
            x = max(screen.left(), min(x, screen.right() - self.width()))
            y = max(screen.top(), min(y, screen.bottom() - self.height()))
            # Check if this position overlaps the pet
            dialog_rect = QRect(x, y, self.width(), self.height())
            if not dialog_rect.intersects(pet_geometry):
                self.move(QPoint(x, y))
                return

        # Fallback: above the pet
        x = max(screen.left(), min(px - self.width() // 2, screen.right() - self.width()))
        y = max(screen.top(), pet_geometry.top() - self.height() - 8)
        self.move(QPoint(x, y))

    def _append_text(self, role, color, text):
        safe = html_escape(text)
        self.history_view.append(
            f'<p><b style="color:{color}">{role}:</b> {safe}</p>'
        )

    def _send_message(self):
        text = self.input_box.text().strip()
        if not text or self._streaming:
            return
        self.input_box.clear()
        self.input_box.setEnabled(False)

        self._append_text("你", "#88ccff", text)
        self._history.append({"role": "user", "content": text})
        self._save_history()
        self._streaming = True

        if self.ai:
            self._append_text("🐱 宠物", "#FF8C42", "思考中...")
            threading.Thread(target=self._call_ai, args=(text,), daemon=True).start()
        else:
            self._append_text("🐱 宠物", "#FF8C42",
                              "（未配置 API Key，请编辑 config.json）")
            self._streaming = False
            self.input_box.setEnabled(True)

    def _call_ai(self, user_text):
        try:
            system = (
                "你是一只住在用户桌面上的像素猫宠物。"
                "回复要简短、可爱、有帮助，一两句话就好。"
                "偶尔加个'喵~'。用中文回复。"
            )
            msgs = [{"role": "system", "content": system}] + self._history[-6:]
            result = self.ai.chat_sync(msgs)
            self._result_signal.emit(result)
        except Exception as e:
            self._error_signal.emit(str(e))

    def _on_result(self, text):
        self._append_text("🐱 宠物", "#FF8C42", text)
        self._streaming = False
        self._history.append({"role": "assistant", "content": text})
        self._save_history()
        self.input_box.setEnabled(True)

    def _on_error(self, err):
        self._append_text("🐱 宠物", "#FF8C42", f"（出错了：{err}）")
        self._streaming = False
        self.input_box.setEnabled(True)

    def show_analysis(self, text):
        self.history_view.clear()
        self._append_text("🐱 宠物", "#FF8C42", text)
        self._history.append({"role": "assistant", "content": text})
        self._save_history()
        self.show()
        self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self.input_box.setFocus()

    def eventFilter(self, obj, event):
        # Esc key anywhere -> dismiss dialog
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self._dismiss()
                return True
        # Mouse click outside dialog -> dismiss dialog
        if event.type() == QEvent.MouseButtonPress:
            pos = event.globalPos() if hasattr(event, 'globalPos') else event.globalPosition().toPoint()
            if not self.geometry().contains(pos):
                self._dismiss()
                return True
        return super().eventFilter(obj, event)

    def _dismiss(self):
        """Hide dialog without quitting the app."""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        self.hide()
        self.closed.emit()

    def closeEvent(self, event):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        self.closed.emit()
        super().closeEvent(event)
