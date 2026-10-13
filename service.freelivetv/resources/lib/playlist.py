"""Download, clean and write the M3U playlist. No Kodi imports."""
import json
import os
import time
import urllib.request

from resources.lib import debuglog
from resources.lib.constants import BASE_URL, COUNTRIES_API, USER_AGENT


def source_url(code):
    code = (code or "").strip().lower()
    if code in ("", "all"):
        return "%s/index.m3u" % BASE_URL
    return "%s/countries/%s.m3u" % (BASE_URL, code)


def _get(url, timeout=30):
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        debuglog.debug("GET %s -> %s, %d bytes, %d ms" % (
            url, getattr(resp, "status", "?"), len(body), (time.time() - t0) * 1000))
        return body.decode("utf-8", errors="replace")


def parse(text):
    """Return a list of {meta: [#EXTINF, #EXTVLCOPT...], url, name}."""
    entries, block = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            block = [line]
        elif line.startswith("#"):
            if block:
                block.append(line)  # keeps #EXTVLCOPT referrer / user-agent lines
        elif block:
            name = block[0].rsplit(",", 1)[-1].strip()
            entries.append({"meta": block, "url": line, "name": name})
            block = []
    return entries


def clean(entries, dedupe=True):
    if dedupe:
        seen, unique = set(), []
        for e in entries:
            if e["url"] not in seen:
                seen.add(e["url"])
                unique.append(e)
        entries = unique
    return sorted(entries, key=lambda e: e["name"].casefold())


def render(entries):
    out = ["#EXTM3U"]
    for e in entries:
        out.extend(e["meta"])
        out.append(e["url"])
    return "\n".join(out) + "\n"


def load_entries(code, dedupe=True):
    """Download + parse + clean. Returns the FULL list (no dead-stream filtering)."""
    return clean(parse(_get(source_url(code))), dedupe)


def generate(code, out_path, dedupe=True, dead=None):
    """Write the playlist atomically. Returns (kept, hidden).
    Raises on network error or empty playlist, leaving any old file untouched."""
    entries = load_entries(code, dedupe)
    if not entries:
        raise ValueError("playlist is empty")
    total = len(entries)
    if dead:
        alive = [e for e in entries if e["url"] not in dead]
        if alive:  # never end up with an empty list because of filtering
            entries = alive
        else:
            debuglog.warn("Every channel is marked dead - ignoring the dead-stream filter")
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(render(entries))
    os.replace(tmp, out_path)
    return len(entries), total - len(entries)


def list_countries():
    """[(code, name)] sorted by name, from the iptv-org API."""
    data = json.loads(_get(COUNTRIES_API))
    return sorted(((c["code"], c["name"]) for c in data), key=lambda c: c[1].casefold())
