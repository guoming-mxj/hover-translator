# -*- coding: utf-8 -*-
"""简单文件日志，便于排查取词/翻译问题"""
import os
import sys
import time
import threading


def _base_dir():
    """打包成 exe 后返回 exe 所在目录；源码运行返回脚本目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


_LOG = os.path.join(_base_dir(), "debug.log")
_lock = threading.Lock()


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _lock:
        try:
            with open(_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    print(line)
