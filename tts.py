# -*- coding: utf-8 -*-
"""发音：SAPI（系统自带，离线）/ edge-tts（联网，自然）"""
import os
import tempfile
import threading

import config
import app_log

_sapi_engine = None
_sapi_lock = threading.Lock()


def speak(text):
    if not text:
        return
    # 独立非守护线程播放，避免被主循环回收，也不阻塞 UI
    threading.Thread(target=_speak_worker, args=(text,)).start()


def _speak_worker(text):
    if config.TTS_ENGINE == "edge":
        try:
            _speak_edge(text)
            return
        except Exception as e:
            app_log.log(f"edge 发音失败，回退 SAPI: {e}")
    try:
        _speak_sapi(text)
    except Exception as e:
        app_log.log(f"SAPI 发音异常: {e}")


def _select_english_voice(engine):
    """显式挑选英文嗓音：优先 en-US，其次任意 English"""
    voices = engine.getProperty("voices")
    # 第一轮：美式英文
    for v in voices:
        name = (getattr(v, "name", "") or "").lower()
        vid = (getattr(v, "id", "") or "").lower()
        if "en-us" in vid or ("english" in name and "united states" in name):
            engine.setProperty("voice", v.id)
            return v.name
    # 第二轮：任意英文
    for v in voices:
        name = (getattr(v, "name", "") or "").lower()
        if "english" in name:
            engine.setProperty("voice", v.id)
            return v.name
    return None


def _speak_sapi(text):
    # 每次都使用全新引擎实例，用完即弃：
    # 复用全局引擎在快速/重复调用时 runAndWait 会瞬间返回导致"静默"
    with _sapi_lock:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", config.TTS_RATE)
        chosen = _select_english_voice(engine)
        app_log.log(f"SAPI 播放: {text!r} 嗓音={chosen!r}")
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass
        app_log.log("SAPI 播放完成")


def _speak_edge(text):
    import edge_tts
    from playsound import playsound

    out = os.path.join(tempfile.gettempdir(), "hover_tts.mp3")
    communicate = edge_tts.Communicate(text, config.EDGE_VOICE)
    communicate.save_sync(out)
    playsound(out)
