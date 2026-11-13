# -*- coding: utf-8 -*-
"""
翻译模块：
- youdao:   有道免费 web 接口（无需 key，联网）
- mymemory: MyMemory 免费接口（无需 key，联网，适合单词）
- offline_argos: Argos Translate 离线神经翻译（需 pip install argostranslate
                  并下载 en->zh 语言包）
带 JSON 本地缓存。
"""
import json
import os
import time
import hashlib
import threading
import urllib.parse

import requests

import config

_lock = threading.Lock()
_cache = {}


# ---------------- 缓存 ----------------

def _load_cache():
    global _cache
    try:
        if os.path.exists(config.CACHE_FILE):
            with open(config.CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
    except Exception:
        _cache = {}


def _save_cache():
    try:
        if len(_cache) > config.CACHE_SIZE:
            # 简单淘汰：丢掉最早的一半
            keys = list(_cache.keys())
            for k in keys[: len(keys) // 2]:
                _cache.pop(k, None)
        with open(config.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def translate(text):
    """英译中，返回译文（字符串）。失败返回 None"""
    text = (text or "").strip()
    if not text:
        return None

    key = config.TRANSLATE_ENGINE + ":" + text.lower()
    with _lock:
        if key in _cache:
            return _cache[key]

    engine = {
        "bing": _translate_bing,
        "mymemory": _translate_mymemory,
        "youdao": _translate_youdao,
        "offline_argos": _translate_argos,
    }.get(config.TRANSLATE_ENGINE, _translate_bing)

    result = None
    try:
        result = engine(text)
    except Exception:
        pass
    if not result:
        # 当前引擎失败时，依次尝试备用在线引擎
        for fallback in (_translate_bing, _translate_mymemory):
            if fallback is engine:
                continue
            try:
                result = fallback(text)
                if result:
                    break
            except Exception:
                continue

    if result:
        with _lock:
            _cache[key] = result
            _save_cache()
    return result


# ---------------- 有道免费接口 ----------------

def _translate_youdao(text):
    # 有道 fanyi 网页公开接口（fanyideskweb 老接口，仅适合低频本地使用）
    ts = int(time.time() * 1000)
    salt = str(ts)
    sign_str = "fanyideskweb" + text + salt + "Ygy_4c=r#e#4EX^NUGUc5"
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    data = {
        "i": text,
        "from": "en",
        "to": "zh-CHS",
        "smartresult": "dict",
        "client": "fanyideskweb",
        "salt": salt,
        "sign": sign,
        "lts": ts,
        "bv": "md5(client)",
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "action": "FY_BY_REALTlME",
    }
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120 Safari/537.36"),
        "Referer": "https://fanyi.youdao.com/",
    }
    resp = requests.post(
        "https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule",
        data=data, headers=headers, timeout=config.TRANSLATE_TIMEOUT)
    j = resp.json()

    # 词典结果（单词）：包含音标/多个释义
    parts = []
    smart = j.get("smartResult") or {}
    dict_result = smart.get("entries") or []
    dict_result = [e for e in dict_result if e]
    if dict_result:
        parts.append("；".join(dict_result[:8]))

    # 机器翻译结果（句子）
    trans_lines = []
    for seg in (j.get("translateResult") or []):
        line = "".join(item.get("tgt", "") for item in seg)
        if line:
            trans_lines.append(line)
    if trans_lines:
        parts.append("\n".join(trans_lines))

    return "\n".join(p for p in parts if p).strip() or None


# ---------------- Bing（必应网页接口，无需 Key，句子效果好） ----------------

def _translate_bing(text):
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120 Safari/537.36"),
        "Referer": "https://cn.bing.com/translator",
    }
    sess = requests.Session()
    # 先拿 IG 和 key
    home = sess.get("https://cn.bing.com/translator", headers=headers,
                    timeout=config.TRANSLATE_TIMEOUT)
    import re
    ig = re.search(r'IG:"([^"]+)"', home.text)
    params = {"IG": ig.group(1) if ig else ""}
    token = re.search(r'params_AbusePreventionHelper\s*=\s*\[\s*(\d+)\s*,\s*"([^"]+)"',
                      home.text)
    if not token:
        return None
    data = {
        "fromLang": "en",
        "text": text,
        "to": "zh-Hans",
        "token": token.group(2),
        "key": token.group(1),
        "tryFetchingGenderDebiasedTranslations": "true",
    }
    headers2 = dict(headers)
    headers2["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    resp = sess.post(
        f"https://cn.bing.com/ttranslatev3?isVertical=1&&IG={params['IG']}"
        f"&IID=translator.5028.1",
        data=data, headers=headers2, timeout=config.TRANSLATE_TIMEOUT)
    j = resp.json()
    return j[0]["translations"][0]["text"]


# ---------------- MyMemory ----------------

def _translate_mymemory(text):
    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": "en|zh-CN"}
    resp = requests.get(url, params=params, timeout=config.TRANSLATE_TIMEOUT)
    j = resp.json()
    data = j.get("responseData") or {}
    translated = data.get("translatedText")
    if translated:
        return urllib.parse.unquote(translated)
    return None


# ---------------- Argos 离线 ----------------

_argos_model = None


def _translate_argos(text):
    global _argos_model
    try:
        import argostranslate.translate
    except ImportError:
        raise RuntimeError("未安装 argostranslate：pip install argostranslate")

    if _argos_model is None:
        argostranslate.translate.package_installer.update_package_index()
        pkgs = argostranslate.translate.package_installer.get_available_packages()
        pkg = next((p for p in pkgs if p.from_code == "en"
                    and p.to_code in ("zh", "zh_cn")), None)
        if pkg is None:
            raise RuntimeError("未找到 en->zh 语言包")
        argostranslate.translate.package_installer.install_from_path(
            pkg.download())
        _argos_model = True
    return argostranslate.translate.translate(text, "en", "zh")


_load_cache()
