# -*- coding: utf-8 -*-
"""
文本抓取：
1) UIA（UI Automation）—— 对可选中文本的软件（浏览器/记事本/Office/资源管理器等）直接取词
2) RapidOCR —— 对图片、自绘界面、游戏、PDF 渲染区等不可选中文本截屏识别兜底
"""
import re
import time
import threading

import config

# ---------------- OCR 懒加载（模型加载较慢，只在首次需要时加载） ----------------
_ocr_engine = None
_ocr_lock = threading.Lock()
_last_ocr_time = 0.0


def _get_ocr():
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
    return _ocr_engine


# ---------------- UIA 取词 ----------------

def _uia_word_at(x, y):
    """
    利用 pywinauto 的 UIA 后端获取鼠标下的文本。
    优先取被悬停的"单词/句子"；拿不到则返回 None。
    """
    try:
        from pywinauto import Desktop
        from pywinauto.uia_element_info import UIAElementInfo
        import win32gui
        import win32process
        import psutil
    except Exception:
        return None

    try:
        # 过滤自身进程窗口
        hwnd = win32gui.WindowFromPoint((x, y))
        if hwnd:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                exe = (psutil.Process(pid).name() or "").lower()
                if exe in {e.lower() for e in config.BLACKLIST_EXE}:
                    return None
            except Exception:
                pass

        elem = UIAElementInfo.from_point(x, y)
    except Exception:
        return None

    if elem is None:
        return None

    # 1) Text/Edit 控件：读整段文本，再按鼠标位置切出单词
    for attempt in ("control", "parent"):
        try:
            target = elem if attempt == "control" else elem.parent
            if target is None:
                continue
            ctype = (target.control_type or "").lower()
            if ctype not in ("text", "edit", "document", "hyperlink", "button",
                             "menuitem", "tabitem", "listitem", "combobox"):
                continue
            full_text = (target.window_text or target.name or "").strip()
            if full_text and _contains_english(full_text):
                return _pick_word(full_text)
        except Exception:
            continue

    # 2) 支持 TextPattern 的控件（Chrome/Edge/Firefox 网页正文等）
    try:
        import ctypes
        from pywinauto.uia_defines import IUIA

        uia = IUIA()
        uia_elem = elem._element  # 底层 IUIAutomationElement
        # 获取 TextPattern
        pattern_id = uia.GetPatternId("TextPatternId") \
            if hasattr(uia, "GetPatternId") else 10014
        pattern = uia_elem.GetCurrentPattern(pattern_id)
        if pattern:
            # 取全部文本范围
            doc_range = pattern.DocumentRange
            full_text = doc_range.GetText(5000) or ""
            if full_text and _contains_english(full_text):
                return _pick_word(full_text)
    except Exception:
        pass

    return None


# ---------------- OCR 取词 ----------------

def _ocr_word_at(x, y):
    global _last_ocr_time
    if not config.ENABLE_OCR_FALLBACK:
        return None

    now = time.time()
    if now - _last_ocr_time < config.OCR_MIN_INTERVAL:
        return None
    _last_ocr_time = now

    try:
        import mss
        import numpy as np
        from PIL import Image

        left = int(x - config.OCR_REGION_W / 2)
        top = int(y - config.OCR_REGION_H / 2)
        bbox = {
            "left": max(left, 0),
            "top": max(top, 0),
            "width": config.OCR_REGION_W,
            "height": config.OCR_REGION_H,
        }
        with mss.mss() as sct:
            shot = sct.grab(bbox)
            img = Image.frombytes("RGB", shot.size, shot.rgb)

        img = img.resize((img.width * config.OCR_SCALE,
                          img.height * config.OCR_SCALE))
        arr = np.array(img)

        ocr = _get_ocr()
        result, _ = ocr(arr)
        if not result:
            return None

        cx = (x - max(left, 0)) * config.OCR_SCALE
        cy = (y - max(top, 0)) * config.OCR_SCALE

        # 找到包含鼠标点的文本行；否则取距离最近的一行
        best_line = None
        best_dist = float("inf")
        for box, text, score in result:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            if x0 - 10 <= cx <= x1 + 10 and y0 - 10 <= cy <= y1 + 10:
                best_line = text
                break
            # 到行框的最近点距离
            dx = max(x0 - cx, 0, cx - x1)
            dy = max(y0 - cy, 0, cy - y1)
            dist = dx * dx + dy * dy
            if dist < best_dist:
                best_dist = dist
                best_line = text

        if best_line and _contains_english(best_line):
            return _pick_word(best_line)
    except Exception:
        return None

    return None


# ---------------- 公共入口 ----------------

# 浏览器渲染窗口类名：这些窗口里 UIA 默认取不到网页文本，直接走 OCR
_BROWSER_RENDER_CLASSES = (
    "chrome_renderwidgethosthwnd",   # Chrome / Edge
    "mozillawindowclass",            # Firefox
    "mozillacontentwindowclass",
)


def _window_class_at(x, y):
    try:
        import win32gui
        hwnd = win32gui.WindowFromPoint((x, y))
        if hwnd:
            return (win32gui.GetClassName(hwnd) or "").lower()
    except Exception:
        pass
    return ""


def grab_text_at(x, y):
    """返回鼠标下的英文单词/短语，失败返回 None"""
    import app_log

    wclass = _window_class_at(x, y)
    is_browser = any(c in wclass for c in _BROWSER_RENDER_CLASSES)

    if is_browser:
        # 浏览器：先试 UIA（用户可能开了辅助功能），取不到立即 OCR
        text = _uia_word_at(x, y)
        app_log.log(f"浏览器窗口 class={wclass}, UIA取词={text!r}")
        if text:
            return text
        text = _ocr_word_at(x, y)
        app_log.log(f"浏览器 OCR取词={text!r}")
        return text

    # 其他软件：UIA 优先，失败 OCR
    text = _uia_word_at(x, y)
    if text:
        return text
    return _ocr_word_at(x, y)


def preheat_ocr():
    """启动时后台预热 OCR 模型，避免首次悬停等待"""
    def _w():
        try:
            _get_ocr()
            import app_log
            app_log.log("OCR 模型预热完成")
        except Exception as e:
            import app_log
            app_log.log(f"OCR 预热失败: {e}")
    threading.Thread(target=_w, daemon=True).start()


# ---------------- 工具函数 ----------------

_ENGLISH_RE = re.compile(r"[A-Za-z]")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _contains_english(s):
    return bool(_ENGLISH_RE.search(s or ""))


def _pick_word(text):
    """
    从一段文本中提取目标词：
    - 短文本（按钮/菜单）整体返回（最多若干词）
    - 长文本返回中间最可能的英文单词
    """
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()

    words = _WORD_RE.findall(text)
    if not words:
        return None

    # 整体只有 1~4 个英文单词且文本较短，按短语处理
    stripped = re.sub(r"[^A-Za-z'’\-\s]", "", text).strip()
    stripped = stripped.strip("-'’")  # 去掉首尾连字符/引号噪声
    if len(text) <= 40 and len(words) <= 4:
        return stripped.lower()

    # 长文本：取中间的"实词"（跳过太短的 of/the/a 等停用词）
    stop = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or",
            "is", "are", "was", "were", "be", "for", "with", "by", "as"}
    middle = words[len(words) // 2 - 1: len(words) // 2 + 2] or words
    for w in middle:
        if w.lower() not in stop and len(w) > 1:
            return w.lower()
    return words[len(words) // 2].lower()
