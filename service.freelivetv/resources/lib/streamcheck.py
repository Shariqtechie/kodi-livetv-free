"""On-demand stream tester with a persistent result cache. No Kodi imports."""
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from resources.lib import paths
from resources.lib.constants import CHECK_TIMEOUT, CHECK_WORKERS, DEFAULT_UA

PRUNE_DAYS = 30
# We only test reachability, so don't fail streams over certificate problems.
_CTX = ssl._create_unverified_context()


# ---- cache: {url: [ok(1/0), checked_at, reason]} ----------------------------------------

def load_cache():
    try:
        with open(paths.cache_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", {}) if data.get("v") == 1 else {}
    except Exception:
        return {}


def save_cache(items):
    cutoff = time.time() - PRUNE_DAYS * 86400
    items = {u: v for u, v in items.items() if v[1] >= cutoff}
    tmp = paths.cache_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"v": 1, "items": items}, f, separators=(",", ":"))
    os.replace(tmp, paths.cache_path())
    return items


def dead_urls(items=None):
    items = load_cache() if items is None else items
    return {u for u, v in items.items() if not v[0]}


def needs_check(url, items, ttl_seconds):
    v = items.get(url)
    return v is None or time.time() - v[1] > ttl_seconds


# ---- the check itself ------------------------------------------------------------------

def _headers(entry):
    h = {"User-Agent": DEFAULT_UA}
    for line in entry["meta"][1:]:
        if line.upper().startswith("#EXTVLCOPT:"):
            key, _, val = line[11:].partition("=")
            key = key.strip().lower()
            if key == "http-user-agent":
                h["User-Agent"] = val.strip()
            elif key in ("http-referrer", "http-referer"):
                h["Referer"] = val.strip()
    return h


def _reason(exc):
    inner = getattr(exc, "reason", exc)
    if isinstance(inner, (socket.timeout, TimeoutError)):
        return "timeout"
    if isinstance(inner, ConnectionRefusedError):
        return "refused"
    if isinstance(inner, socket.gaierror):
        return "dns"
    if isinstance(inner, ssl.SSLError):
        return "ssl"
    return type(inner).__name__


def check_entry(entry, timeout=CHECK_TIMEOUT):
    """Returns (ok, reason, milliseconds). ok=None means 'cannot test' (not cached)."""
    url = entry["url"]
    if not url.lower().startswith(("http://", "https://")):
        return None, "unsupported scheme", 0
    t0 = time.time()

    def ms():
        return int((time.time() - t0) * 1000)

    try:
        req = urllib.request.Request(url, headers=_headers(entry))
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            status = getattr(resp, "status", 200)
            chunk = resp.read(4096)
    except urllib.error.HTTPError as e:
        return False, "HTTP %d" % e.code, ms()
    except Exception as e:
        return False, _reason(e), ms()

    if status >= 400:
        return False, "HTTP %d" % status, ms()
    if not chunk:
        return False, "empty", ms()
    path = url.split("?")[0].lower()
    if path.endswith((".m3u8", ".m3u")) and b"#EXTM3U" not in chunk:
        return False, "not a playlist", ms()
    return True, "ok", ms()


def run(entries, progress_cb, results=None, workers=CHECK_WORKERS, timeout=CHECK_TIMEOUT):
    """Check entries in parallel. progress_cb(done, total, alive, dead) -> True to cancel.
    Fills `results` ({url: (ok, reason, ms)}) as it goes, so the caller keeps partial
    results even if something raises. Returns (results, cancelled).
    Python 3.8 compatible: Kodi on Windows bundles 3.8 (no Executor.shutdown(cancel_futures))."""
    results = {} if results is None else results
    done = alive = dead = 0
    total = len(entries)
    ex = ThreadPoolExecutor(max_workers=workers)
    futures = {ex.submit(check_entry, e, timeout): e for e in entries}
    cancelled = False
    try:
        for fut in as_completed(futures):
            ok, reason, took = fut.result()
            done += 1
            if ok is not None:
                results[futures[fut]["url"]] = (ok, reason, took)
                alive += 1 if ok else 0
                dead += 0 if ok else 1
            if progress_cb(done, total, alive, dead):
                cancelled = True
                break
    finally:
        for fut in futures:
            fut.cancel()  # drop anything still queued
        ex.shutdown(wait=False)
    return results, cancelled
