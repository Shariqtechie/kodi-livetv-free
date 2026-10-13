"""Logging: always to kodi.log, plus our own small log file.

- info/warn/error  -> kodi.log + our file (always, so problems are never lost)
- debug            -> only when 'Debug logging' is ON in settings. Written at INFO level in
                      kodi.log on purpose, so you do NOT need to enable Kodi's global debug mode.
"""
import threading
import time

try:
    import xbmc
except ImportError:  # local tests outside Kodi
    xbmc = None

from resources.lib import paths
from resources.lib.constants import ADDON_ID, LOG_MAX_BYTES

_lock = threading.Lock()
_cache = {"t": 0.0, "v": False}


def debug_enabled():
    now = time.time()
    if now - _cache["t"] > 3:  # don't hit the settings API on every line
        _cache["t"] = now
        try:
            import xbmcaddon
            _cache["v"] = xbmcaddon.Addon(ADDON_ID).getSettingBool("debug_enabled")
        except Exception:
            _cache["v"] = False
    return _cache["v"]


def _emit(level, msg, kodi_level):
    if xbmc is not None:
        xbmc.log("[%s] %s" % (ADDON_ID, msg), kodi_level)
    else:
        print("%s %s" % (level, msg))
    line = "%s %-5s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), level, msg)
    try:
        import os
        with _lock:
            p = paths.log_path()
            if os.path.exists(p) and os.path.getsize(p) > LOG_MAX_BYTES:
                os.replace(p, p + ".1")
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


def info(msg):
    _emit("INFO", msg, xbmc.LOGINFO if xbmc else 0)


def warn(msg):
    _emit("WARN", msg, xbmc.LOGWARNING if xbmc else 0)


def error(msg):
    _emit("ERROR", msg, xbmc.LOGERROR if xbmc else 0)


def debug(msg):
    if debug_enabled():
        _emit("DEBUG", msg, xbmc.LOGINFO if xbmc else 0)


def read(max_bytes=300 * 1024):
    """Our log (previous + current file), newest part only."""
    import os
    p = paths.log_path()
    text = ""
    for f in (p + ".1", p):
        if os.path.exists(f):
            with open(f, encoding="utf-8", errors="replace") as fh:
                text += fh.read()
    return text[-max_bytes:] if text else "(log is empty)"
