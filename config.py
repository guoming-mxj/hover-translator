# -*- coding: utf-8 -*-
"""全局配置"""
import os
import sys


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

# ============ 触发方式 ============
# 鼠标悬停多少秒后触发翻译
HOVER_DELAY = 0.45
# 鼠标在多少像素内移动视为"静止悬停"
HOVER_PIXEL_TOLERANCE = 6
# 是否要求按住修饰键才翻译（False = 纯悬停即翻译）
REQUIRE_MODIFIER = False
MODIFIER_KEY = "ctrl"          # ctrl / alt / shift，REQUIRE_MODIFIER=True 时生效

# ============ 取词 ============
# UIA 取词失败后是否启用 OCR 截屏兜底（图片/游戏/PDF 渲染区等）
ENABLE_OCR_FALLBACK = True
# OCR 截图区域：以鼠标为中心的宽/高（像素）
OCR_REGION_W = 520
OCR_REGION_H = 120
# 放大倍数（先放大再识别，小字号更准）
OCR_SCALE = 2
# 单次 OCR 最小间隔（秒），避免频繁跑模型卡顿
OCR_MIN_INTERVAL = 0.6

# ============ 音标 ============
# 是否查询并显示 IPA 音标（仅单词有效，免费词典 API，需联网）
SHOW_PHONETIC = True
PHONETIC_TIMEOUT = 4
# 音标偏好："us" 美式优先 | "uk" 英式优先
PHONETIC_PREFER = "us"

# ============ 翻译 ============
# 翻译引擎: "bing" | "mymemory" | "offline_argos"
TRANSLATE_ENGINE = "bing"
TRANSLATE_TIMEOUT = 5
# 翻译结果本地缓存条数
CACHE_SIZE = 1000
CACHE_FILE = os.path.join(_base_dir(), "cache.json")

# ============ 发音 ============
# 发音引擎: "sapi"（Windows 自带，完全离线） | "edge"（edge-tts，联网更自然）
TTS_ENGINE = "sapi"
TTS_RATE = 170                 # sapi 语速
# edge-tts 嗓音（美音/英音）
EDGE_VOICE = "en-US-AriaNeural"

# ============ 弹窗 ============
POPUP_MAX_WIDTH = 420
POPUP_BG = "#1e1e2e"
POPUP_FG = "#cdd6f4"
POPUP_ACCENT = "#89b4fa"

# 不处理的窗口类名/进程名（可选，减少干扰），小写匹配
BLACKLIST_EXE = {"hover_translator.exe", "python.exe"}  # 自身窗口不取词
