# -*- coding: utf-8 -*-
"""
词典信息：IPA 音标
免费接口 https://api.dictionaryapi.dev（无需 Key），只对单词有效。
短语/句子或查询失败时返回 None，不影响翻译流程。
"""
import re
import requests

import config

_PHON_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")  # 纯单词才查
_cache = {}


def get_phonetic(word):
    """返回音标字符串，如 '/ˈhæpi/'，失败返回 None"""
    word = (word or "").strip().lower()
    if not word or " " in word or not _PHON_RE.match(word):
        return None
    if word in _cache:
        return _cache[word]

    result = None
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
            timeout=config.PHONETIC_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            result = _extract_phonetic(data)
    except Exception:
        result = None

    _cache[word] = result
    return result


def _extract_phonetic(data):
    # data: [{"phonetic": "/.../", "phonetics": [{"text":..., "audio":...}]}]
    if not isinstance(data, list) or not data:
        return None
    entry = data[0]

    phonetics = entry.get("phonetics") or []
    prefer_audio = "-us.mp3" if config.PHONETIC_PREFER == "us" else "-uk.mp3"

    # 1) 按偏好口音（audio URL 里区分 uk/us）
    for p in phonetics:
        audio = p.get("audio") or ""
        text = p.get("text")
        if text and prefer_audio in audio:
            return text

    # 2) 任意带 text 的音标
    for p in phonetics:
        if p.get("text"):
            return p["text"]

    # 3) 顶层 phonetic
    top = entry.get("phonetic")
    return top if top else None
