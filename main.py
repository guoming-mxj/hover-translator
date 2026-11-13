# -*- coding: utf-8 -*-
"""
全局悬停翻译器 - 主程序

功能：
  鼠标在屏幕任意位置（网页/软件/图片…）静止悬停 -> 自动抓取英文单词/短语
  -> 英译中 -> 弹窗显示结果 -> 点击🔊或按快捷键播放发音
  右键托盘图标可退出；Esc 关闭弹窗。
"""
import sys
import time
import threading

from pynput import mouse, keyboard

import config
import text_grabber
import translator
import dictionary
import tts
import app_log
from popup import TranslationPopup
from tray import TrayController

# ---------- 全局状态 ----------
_state = {
    "last_move": time.time(),
    "x": 0, "y": 0,
    "last_word": None,
    "last_query_time": 0.0,
    "modifier_pressed": False,
    "running": True,
}


def on_move(x, y):
    _state["x"], _state["y"] = x, y
    _state["last_move"] = time.time()


def on_click(x, y, button, pressed):
    if not pressed:
        return
    # 点击发生在弹窗内部（如点 🔊 / ✕）时不要关窗，交给 tkinter 处理
    try:
        if popup.is_visible() and popup.pointer_inside(x, y):
            return
    except Exception:
        pass
    # 在其它地方点击：收起弹窗
    popup.hide()
    _state["last_word"] = None


def _on_key_press(key):
    try:
        if key == keyboard.Key.esc:
            popup.hide()
            _state["last_word"] = None
        names = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
        an = {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
        sn = {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
        m = {"ctrl": names, "alt": an, "shift": sn}[config.MODIFIER_KEY]
        if key in m:
            _state["modifier_pressed"] = True
    except Exception:
        pass


def _on_key_release(key):
    try:
        all_mods = (
            {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
            | {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
            | {keyboard.Key.shift, keyboard.Key.shift_l,
               keyboard.Key.shift_r})
        if key in all_mods:
            _state["modifier_pressed"] = False
    except Exception:
        pass


# ---------- 悬停检测循环（后台线程） ----------

tray = None  # main() 中赋值为 TrayController 实例


def hover_worker():
    while _state["running"]:
        time.sleep(0.05)
        now = time.time()

        if tray.paused:
            continue
        if now - _state["last_move"] < config.HOVER_DELAY:
            continue
        if config.REQUIRE_MODIFIER and not _state["modifier_pressed"]:
            continue
        if now - _state["last_query_time"] < 0.3:
            continue

        x, y = _state["x"], _state["y"]

        # 鼠标位于弹窗上（正要点 🔊）时，不要重新取词或干扰弹窗
        try:
            if popup.is_visible() and popup.pointer_inside(x, y):
                continue
        except Exception:
            pass
        # OCR 开关（托盘控制）
        ocr_backup = config.ENABLE_OCR_FALLBACK
        config.ENABLE_OCR_FALLBACK = tray.ocr_on
        word = text_grabber.grab_text_at(x, y)
        config.ENABLE_OCR_FALLBACK = ocr_backup
        if not word:
            continue
        if word == _state["last_word"]:
            continue

        _state["last_word"] = word
        app_log.log(f"悬停触发取词: {word!r} @ {x},{y}")
        _state["last_query_time"] = now

        # 音标（单词才查，开关由托盘控制）
        phon = ""
        if config.SHOW_PHONETIC and tray.phon_on:
            phon = dictionary.get_phonetic(word) or ""

        # 在 tk 主线程中显示 loading
        popup.root.after(0, popup.show_loading, word, x, y, tts.speak, phon)

        def task(w=word, px=x, py=y, ph=phon):
            result = translator.translate(w)
            if result is None:
                popup.root.after(0, popup.show_error, w,
                                 "翻译失败：请检查网络，或切换离线引擎", ph)
            else:
                popup.root.after(0, popup.show_result, w, result, px, py,
                                 tts.speak, False, ph)

        threading.Thread(target=task, daemon=True).start()


# ---------- 启动 ----------

popup = TranslationPopup()


def _quit():
    # 该函数可能在托盘线程被调用，用 after 把退出动作投递到主线程
    def _do():
        _state["running"] = False
        try:
            popup.root.quit()
        except Exception:
            pass
    try:
        popup.root.after(0, _do)
    except Exception:
        _do()


def main():
    global tray
    app_log.log("==== 程序启动 ====")
    tray = TrayController(on_exit=_quit)
    tray.run_thread()

    # 后台预热 OCR 模型（浏览器/图片取词更快）
    if config.ENABLE_OCR_FALLBACK:
        text_grabber.preheat_ocr()

    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    key_listener = keyboard.Listener(on_press=_on_key_press,
                                     on_release=_on_key_release)
    mouse_listener.daemon = True
    key_listener.daemon = True
    mouse_listener.start()
    key_listener.start()

    t = threading.Thread(target=hover_worker, daemon=True)
    t.start()

    # 使用标准 tkinter 主事件循环；后台线程通过 root.after 安全调度 UI
    try:
        popup.root.mainloop()
    except (KeyboardInterrupt, Exception) as e:
        app_log.log(f"主循环异常: {e}")
    finally:
        _state["running"] = False


if __name__ == "__main__":
    sys.exit(main())
