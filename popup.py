# -*- coding: utf-8 -*-
"""轻量 tkinter 翻译弹窗：无边框、置顶、显示原文/译文/发音按钮"""
import tkinter as tk

import config


class TranslationPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)          # 无边框
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.97)
        except tk.TclError:
            pass

        self.frame = tk.Frame(self.root, bg=config.POPUP_BG, bd=1,
                              relief="solid")
        self.frame.pack(fill="both", expand=True)

        self.word_var = tk.StringVar()
        self.phonetic_var = tk.StringVar()
        self.result_var = tk.StringVar()
        self.status_var = tk.StringVar()

        head = tk.Frame(self.frame, bg=config.POPUP_BG)
        head.pack(anchor="w", padx=10, pady=(8, 0), fill="x")

        self.word_label = tk.Label(
            head, textvariable=self.word_var, bg=config.POPUP_BG,
            fg=config.POPUP_ACCENT, font=("Segoe UI", 14, "bold"),
            wraplength=config.POPUP_MAX_WIDTH - 90, justify="left")
        self.word_label.pack(side="left", anchor="w")

        self.phonetic_label = tk.Label(
            head, textvariable=self.phonetic_var, bg=config.POPUP_BG,
            fg="#a6adc8", font=("Segoe UI", 10), padx=6)
        self.phonetic_label.pack(side="left", anchor="w", pady=(4, 0))

        self.result_label = tk.Label(
            self.frame, textvariable=self.result_var, bg=config.POPUP_BG,
            fg=config.POPUP_FG, font=("Microsoft YaHei UI", 11),
            wraplength=config.POPUP_MAX_WIDTH - 20, justify="left")
        self.result_label.pack(anchor="w", padx=10, pady=2)

        self.status_label = tk.Label(
            self.frame, textvariable=self.status_var, bg=config.POPUP_BG,
            fg="#7f849c", font=("Microsoft YaHei UI", 9),
            wraplength=config.POPUP_MAX_WIDTH - 20, justify="left")
        self.status_label.pack(anchor="w", padx=10, pady=(0, 4))

        btn_row = tk.Frame(self.frame, bg=config.POPUP_BG)
        btn_row.pack(anchor="e", padx=8, pady=(0, 8))

        self.speak_btn = tk.Button(
            btn_row, text="🔊 播放", command=self._on_speak,
            bg="#313244", fg=config.POPUP_FG, activebackground="#45475a",
            activeforeground=config.POPUP_FG, relief="flat",
            font=("Microsoft YaHei UI", 9), padx=8, cursor="hand2")
        self.speak_btn.pack(side="left", padx=4)

        self.close_btn = tk.Button(
            btn_row, text="✕", command=self.hide,
            bg="#313244", fg=config.POPUP_FG, activebackground="#45475a",
            activeforeground="#f38ba8", relief="flat",
            font=("Segoe UI", 9), padx=6, cursor="hand2")
        self.close_btn.pack(side="left")

        self._speak_cb = None
        self._after_id = None
        # 鼠标进入弹窗时保持显示；移出后延迟关闭
        self.frame.bind("<Enter>", self._cancel_hide)
        self.frame.bind("<Leave>", self._schedule_hide)

    def _on_speak(self):
        word = (self.word_var.get() or "").strip()
        if word and self._speak_cb:
            import app_log
            app_log.log(f"点击播放: {word!r}")
            self._speak_cb(word)

    def show_loading(self, word, x, y, speak_cb, phonetic=""):
        self._cancel_hide()
        self._speak_cb = speak_cb
        self.word_var.set(word)
        self.phonetic_var.set(phonetic or "")
        self.result_var.set("")
        self.status_var.set("翻译中…")
        self._place(x, y)

    def show_result(self, word, result, x, y, speak_cb, auto_play=False,
                    phonetic=""):
        self._cancel_hide()
        self._speak_cb = speak_cb
        self.word_var.set(word)
        self.phonetic_var.set(phonetic or "")
        self.result_var.set(result or "（无结果）")
        self.status_var.set("")
        self._place(x, y)
        if auto_play and result:
            self._on_speak()

    def show_error(self, word, msg, phonetic=""):
        self.word_var.set(word)
        self.phonetic_var.set(phonetic or "")
        self.result_var.set("")
        self.status_var.set(msg)

    def _place(self, x, y):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        px = x + 18
        py = y + 18
        if px + w > sw - 10:
            px = x - w - 18
        if py + h > sh - 60:
            py = sh - h - 60
        self.root.geometry(f"+{max(px, 5)}+{max(py, 5)}")
        self.root.deiconify()

    def hide(self):
        self._cancel_hide()
        self.root.withdraw()

    def is_visible(self):
        return self.root.state() == "normal"

    def pointer_inside(self, x=None, y=None):
        """判断给定坐标（默认当前鼠标）是否落在弹窗矩形内"""
        if not self.is_visible():
            return False
        self.root.update_idletasks()
        x0 = self.root.winfo_rootx()
        y0 = self.root.winfo_rooty()
        x1 = x0 + self.root.winfo_width()
        y1 = y0 + self.root.winfo_height()
        if x is None or y is None:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
        return x0 <= x <= x1 and y0 <= y <= y1

    def _schedule_hide(self, _=None):
        self._cancel_hide()
        # 留足时间让鼠标从单词移动到按钮；进入弹窗即取消
        self._after_id = self.root.after(450, self._hide_if_outside)

    def _hide_if_outside(self):
        self._after_id = None
        # 二次确认：鼠标确实已不在弹窗上才关闭
        if not self.pointer_inside():
            self.hide()

    def _cancel_hide(self, _=None):
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def pump(self):
        """主线程定时调用，刷新 tkinter 事件"""
        try:
            self.root.update()
        except tk.TclError:
            pass
