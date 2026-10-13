"""Download, clean and write the M3U playlist. No Kodi imports."""
import json
import os
import re
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


_TVG_ID = re.compile(r'tvg-id="([^"]*)"')
_RES = re.compile(r"\((\d{3,4})p\)")


def _quality(entry):
    m = _RES.search(entry["name"])
    return int(m.group(1)) if m else 0


def _tvg_id(entry):
    m = _TVG_ID.search(entry["meta"][0])
    return m.group(1).strip() if m else ""


def merge_duplicates(entries, alive=None):
    """Keep one stream per tvg-id: prefer a stream known to be alive, then the highest
    resolution, then the first listed. Entries without a tvg-id are never merged
    (we can't prove they're the same channel). Order is preserved."""
    alive = alive or set()
    best = {}
    for e in entries:
        key = _tvg_id(e)
        if not key:
            continue
        score = (1 if e["url"] in alive else 0, _quality(e))
        if key not in best or score > best[key][0]:
            best[key] = (score, e)
    return [e for e in entries if not _tvg_id(e) or best[_tvg_id(e)][1] is e]


def generate(code, out_path, dedupe=True, dead=None, merge=False, alive=None):
    """Write the playlist atomically. Returns (kept, hidden_as_dead, merged_duplicates).
    Raises on network error or empty playlist, leaving any old file untouched."""
    entries = load_entries(code, dedupe)
    if not entries:
        raise ValueError("playlist is empty")
    total = len(entries)
    if dead:
        alive_entries = [e for e in entries if e["url"] not in dead]
        if alive_entries:  # never end up with an empty list because of filtering
            entries = alive_entries
        else:
            debuglog.warn("Every channel is marked dead - ignoring the dead-stream filter")
    hidden = total - len(entries)
    merged = 0
    if merge:
        before = len(entries)
        entries = merge_duplicates(entries, alive)
        merged = before - len(entries)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(render(entries))
    os.replace(tmp, out_path)
    return len(entries), hidden, merged


def list_countries():
    """[(code, name)] sorted by name, from the iptv-org API."""
    data = json.loads(_get(COUNTRIES_API))
    return sorted(((c["code"], c["name"]) for c in data), key=lambda c: c[1].casefold())
