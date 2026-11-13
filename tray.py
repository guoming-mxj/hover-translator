# -*- coding: utf-8 -*-
"""系统托盘：动态生成图标，菜单支持暂停/恢复、开关 OCR、开关音标、退出"""
import threading

from PIL import Image, ImageDraw
import pystray


def _make_icon(paused=False):
    """生成一个 64x64 圆角方块 + "译" 字风格的简单图标"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = (137, 180, 250, 255) if not paused else (108, 112, 134, 255)
    d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=fill)
    # 字母 A -> 文 的简化：画一个白色大写 A
    d.line([(22, 46), (32, 18)], fill=(30, 30, 46, 255), width=5)
    d.line([(42, 46), (32, 18)], fill=(30, 30, 46, 255), width=5)
    d.line([(26, 36), (38, 36)], fill=(30, 30, 46, 255), width=4)
    return img


class TrayController:
    def __init__(self, on_exit):
        self._paused = False
        self._ocr_on = True
        self._phon_on = True
        self._on_exit = on_exit

        self.item_pause = pystray.MenuItem(
            "暂停翻译", self._toggle_pause, checked=lambda i: self._paused)
        self.item_ocr = pystray.MenuItem(
            "OCR 取词（图片/游戏）", self._toggle_ocr,
            checked=lambda i: self._ocr_on)
        self.item_phon = pystray.MenuItem(
            "显示音标", self._toggle_phon,
            checked=lambda i: self._phon_on)
        self.item_exit = pystray.MenuItem("退出", self._exit)

        menu = pystray.Menu(
            self.item_pause,
            pystray.Menu.SEPARATOR,
            self.item_ocr,
            self.item_phon,
            pystray.Menu.SEPARATOR,
            self.item_exit,
        )

        self.icon = pystray.Icon(
            "hover_translator", _make_icon(),
            "悬停翻译器（运行中）", menu)

    # -------- 属性给主循环读取 --------
    @property
    def paused(self):
        return self._paused

    @property
    def ocr_on(self):
        return self._ocr_on

    @property
    def phon_on(self):
        return self._phon_on

    # -------- 菜单回调 --------
    def _toggle_pause(self, icon, item):
        self._paused = not self._paused
        icon.icon = _make_icon(self._paused)
        icon.title = "悬停翻译器（已暂停）" if self._paused else "悬停翻译器（运行中）"

    def _toggle_ocr(self, icon, item):
        self._ocr_on = not self._ocr_on

    def _toggle_phon(self, icon, item):
        self._phon_on = not self._phon_on

    def _exit(self, icon, item):
        icon.stop()
        if self._on_exit:
            self._on_exit()

    # -------- 启动（阻塞，需放在独立线程） --------
    def run(self):
        self.icon.run()

    def run_thread(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
