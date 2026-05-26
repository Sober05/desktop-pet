"""Desktop pet main window — transparent, animated, draggable, file-drop target."""
import random
import threading
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import (QPainter, QColor,
                          QDragEnterEvent, QDropEvent, QMouseEvent)

from sprites import SPRITE_SIZE, SCALE, PALETTE, ANIMATIONS
from chat_dialog import ChatBubble
from ai_client import AIClient
from file_handler import build_analysis_prompt
from pet_systems import PetSystems
from error_log import log_error

PET_SIZE = SPRITE_SIZE * SCALE  # 64


class PetWindow(QWidget):
    def __init__(self, ai_client=None):
        super().__init__()
        self.ai = ai_client or AIClient()
        self._chat = None

        # Animation
        self._anim_name = "idle"
        self._anim_frames, self._anim_interval = ANIMATIONS["idle"]
        self._frame_idx = 0
        self._frame_counter = 0

        # Movement
        self._dragging = False
        self._drag_offset = QPoint()
        self._facing_right = True

        self.setAcceptDrops(True)
        self._setup_window()

        # Backend systems (tray, menu, idle, mood, etc.)
        self.sys = PetSystems(self)

        # Animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_animation)
        self._anim_timer.start(self._anim_interval)

        # Restore saved position
        self.sys.restore_position()

    # ─── window ─────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("桌面宠物")

        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            screen.right() - PET_SIZE - 40,
            screen.bottom() - PET_SIZE - 100,
            PET_SIZE + 20, PET_SIZE + 20)

    # ─── animation ──────────────────────────────────────────

    def _tick_animation(self):
        self._frame_counter += 1
        if self._frame_counter >= 4:
            self._frame_counter = 0
            self._frame_idx = (self._frame_idx + 1) % len(self._anim_frames)
            self.update()

    def set_animation(self, name, duration_ms=2000):
        if name not in ANIMATIONS:
            return
        if self.sys.is_sleeping and name not in ("sleep", "idle_blink"):
            return
        self._anim_name = name
        self._anim_frames, self._anim_interval = ANIMATIONS[name]
        self._frame_idx = 0
        self._anim_timer.setInterval(self._anim_interval)
        self.update()
        if name not in ("idle", "sleep"):
            QTimer.singleShot(duration_ms, self._return_to_idle)

    def _return_to_idle(self):
        if not self.sys.is_sleeping:
            self.set_animation("idle")

    def _current_frame(self):
        return self._anim_frames[self._frame_idx % len(self._anim_frames)]

    # ─── paint ──────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        frame = self._current_frame()
        ps = SCALE
        ox = 10

        for row in range(SPRITE_SIZE):
            for col in range(SPRITE_SIZE):
                ch = frame[row][col]
                color_hex = PALETTE.get(ch)
                if color_hex is None:
                    continue
                dc = SPRITE_SIZE - 1 - col if not self._facing_right else col
                painter.fillRect(ox + dc * ps, row * ps, ps, ps, QColor(color_hex))

        # Mood indicator dot
        mood = self.sys.mood
        if mood < 40:
            mc = QColor("#ff6666")
        elif mood < 70:
            mc = QColor("#ffcc66")
        else:
            mc = QColor("#66ff66")
        painter.fillRect(ox + 2, 2, 4, 4, mc)

    # ─── mouse ──────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.sys.is_sleeping:
                self.sys._wake_up()
            self._dragging = True
            self._drag_offset = event.pos()
            self.sys.boost_mood(3)
            self.set_animation("happy", 1500)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            new_pos = event.globalPos() - self._drag_offset
            x, y = self._clamp(new_pos.x(), new_pos.y())
            self.move(x, y)
        else:
            self._facing_right = (event.globalPos().x() > self.geometry().center().x())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            was_drag = self._dragging
            self._dragging = False
            if was_drag:
                delta = event.globalPos() - (self.pos() + self._drag_offset)
                if delta.manhattanLength() < 5:
                    self._open_chat()
                self.sys._save_state()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._open_chat()

    def enterEvent(self, event):
        self.sys.boost_mood(2)
        if self.sys.is_sleeping:
            self.sys._wake_up()

    def contextMenuEvent(self, event):
        self.sys.menu.popup(event.globalPos())

    def _clamp(self, x, y):
        screen = QApplication.primaryScreen().availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        return x, y

    # ─── drag & drop ────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.set_animation("think", 3000)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.sys.boost_mood(10)
            self.set_animation("happy", 2000)
            threading.Thread(target=self._analyze_file, args=(path,),
                             daemon=True).start()
        event.acceptProposedAction()

    def _analyze_file(self, path):
        try:
            system, user = build_analysis_prompt(path)
            msgs = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
            result = self.ai.chat_sync(msgs)
            if self._chat is None:
                self._chat = ChatBubble(ai_client=self.ai)
                self._chat.closed.connect(self._on_chat_closed)
            self._chat.show_analysis(result)
            self._chat.position_near(self.geometry())
        except Exception as e:
            log_error(f"File analysis failed: {e}", exc_info=True)

    # ─── chat ───────────────────────────────────────────────

    def _open_chat(self):
        if self._chat is None:
            self._chat = ChatBubble(ai_client=self.ai)
            self._chat.closed.connect(self._on_chat_closed)
        self._chat.show()
        self._chat.position_near(self.geometry())
        self._chat.raise_()
        self._chat.input_box.setFocus()

    def _on_chat_closed(self):
        self._chat = None

    # ─── clipboard ──────────────────────────────────────────

    def check_clipboard(self):
        self.sys.check_clipboard()

    # ─── quit ───────────────────────────────────────────────

    def _quit_app(self):
        self.sys.save_and_cleanup()
        if self._chat:
            self._chat.close()
        QApplication.quit()

    # ─── close ──────────────────────────────────────────────

    def closeEvent(self, event):
        self.sys._save_state()
        super().closeEvent(event)

    # ─── proxy attributes for systems ───────────────────────

    @property
    def _is_sleeping(self):
        return self.sys.is_sleeping

    @property
    def _mood(self):
        return self.sys.mood

    def _enter_sleep(self):
        self.sys._enter_sleep()

    def _show_bubble(self, text):
        self.sys.show_bubble(text)
