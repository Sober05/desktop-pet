"""Desktop Pet - pixel cat with tray, idle detection, mood, etc."""
import sys
import json
import os
import subprocess
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer

from pet_window import PetWindow
from ai_client import AIClient
from error_log import log_error, log_startup, log_shutdown

CONFIG_PATH = Path(__file__).parent / "config.json"
LOCK_PATH = Path(__file__).parent / ".pet-lock"


def acquire_lock():
    if LOCK_PATH.exists():
        try:
            old_pid = int(LOCK_PATH.read_text().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, old_pid)
            if handle:
                kernel32.CloseHandle(handle)
                return False
        except:
            pass
    LOCK_PATH.write_text(str(os.getpid()))
    return True


def release_lock():
    try:
        LOCK_PATH.unlink()
    except:
        pass


def ensure_config():
    if not CONFIG_PATH.exists():
        cfg = {"api_key": "", "model": "deepseek-chat"}
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        return False
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return bool(cfg.get("api_key"))


def main():
    start_time = time.time()
    log_startup()

    # Create QApplication FIRST, before any other Qt operations
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopPet")
    app.setQuitOnLastWindowClosed(False)

    # Single instance check (needs QApplication for message box)
    if not acquire_lock():
        QMessageBox.information(None, "桌面宠物",
                                "桌面宠物已经在运行中啦~ 看看系统托盘？")
        sys.exit(0)

    exit_code = 0
    try:
        has_key = ensure_config()
        ai = AIClient() if has_key else None

        pet = PetWindow(ai_client=ai)
        pet.show()

        # Health check after 3s
        def health_check():
            if not pet.isVisible():
                log_error("Health check: window not visible, re-showing")
                pet.show()
                pet.raise_()
        QTimer.singleShot(3000, health_check)

        # Initial sleep check
        hour = time.localtime().tm_hour
        if 23 <= hour or hour < 6:
            pet.sys._enter_sleep()

        # Clipboard check every 2s
        cb_timer = QTimer(pet)
        cb_timer.timeout.connect(pet.check_clipboard)
        cb_timer.start(2000)

        # Mood-based proactive chat every 2min
        def proactive_loop():
            if not pet.sys.is_sleeping and pet.sys.mood < 30:
                pet.sys.show_bubble("有点寂寞...来跟我聊聊天喵~")

        mood_timer = QTimer(pet)
        mood_timer.timeout.connect(proactive_loop)
        mood_timer.start(120000)

        if not has_key:
            msg = QMessageBox()
            msg.setWindowTitle("桌面宠物 - 首次设置")
            msg.setText("欢迎！请配置你的 DeepSeek API Key。\n\n"
                        "没有 API Key 宠物也能运行，但 AI 功能不可用。")
            msg.setInformativeText("编辑 config.json 填入 Key 后重启即可。")
            msg.setIcon(QMessageBox.Information)
            msg.exec_()

        exit_code = app.exec_()

    except Exception as e:
        log_error("Fatal crash", exc_info=True)
        exit_code = 1
    finally:
        log_shutdown()
        release_lock()

    # Crash watchdog
    runtime = time.time() - start_time
    if runtime < 10 and exit_code != 0:
        log_error(f"Watchdog restart (runtime={runtime:.1f}s)")
        time.sleep(1)
        subprocess.Popen([sys.executable, __file__])

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
