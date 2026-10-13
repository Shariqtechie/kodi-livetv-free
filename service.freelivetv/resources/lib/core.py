import os
import time
import traceback
from collections import Counter

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import debuglog, paths, playlist, pvr_setup, streamcheck
from resources.lib.constants import ADDON_ID, ADDON_NAME


def addon():
    return xbmcaddon.Addon(ADDON_ID)


def tr(string_id):
    return addon().getLocalizedString(string_id)


def notify(msg):
    xbmcgui.Dialog().notification(ADDON_NAME, msg, xbmcgui.NOTIFICATION_INFO, 4000)


# kept for service.py / script.py
playlist_path = paths.playlist_path
flag_path = paths.flag_path


# ---- playlist --------------------------------------------------------------------------

def refresh_playlist(show_notice=False):
    """Returns the number of channels written, or 0 on failure."""
    a = addon()
    country = a.getSetting("country")
    dead = streamcheck.dead_urls() if a.getSettingBool("hide_dead") else set()
    t0 = time.time()
    try:
        kept, hidden = playlist.generate(
            country, paths.playlist_path(), a.getSettingBool("dedupe"), dead
        )
    except Exception as e:  # network down, bad country code, empty list...
        debuglog.error("Playlist refresh failed (country=%r): %s: %s" % (country, type(e).__name__, e))
        debuglog.debug(traceback.format_exc())
        if show_notice:
            notify(tr(30102))
        return 0
    debuglog.info("Playlist updated: country=%s, %d channels written, %d hidden as dead, %d ms" % (
        country, kept, hidden, (time.time() - t0) * 1000))
    if show_notice:
        notify(tr(30101).format(kept))
    return kept


def setup(monitor):
    """Refresh playlist, install IPTV Simple if missing, configure it."""
    debuglog.info("Setup started")
    if not refresh_playlist(show_notice=True) and not os.path.exists(paths.playlist_path()):
        debuglog.error("Setup aborted: no playlist available")
        return False
    if not pvr_setup.ensure_installed(monitor):
        debuglog.error("Setup aborted: IPTV Simple could not be installed")
        notify(tr(30104))
        return False
    minutes = addon().getSettingInt("refresh_hours") * 60
    pvr_setup.configure(paths.playlist_path(), minutes, monitor)
    with open(paths.flag_path(), "w") as f:
        f.write("done")
    debuglog.info("Setup finished")
    notify(tr(30103))
    return True


def choose_country():
    try:
        countries = playlist.list_countries()
    except Exception as e:
        debuglog.error("Country list failed: %s: %s" % (type(e).__name__, e))
        notify(tr(30102))
        return
    labels = [tr(30106)] + ["%s (%s)" % (name, code) for code, name in countries]
    idx = xbmcgui.Dialog().select(tr(30105), labels)
    if idx < 0:
        return
    code = "all" if idx == 0 else countries[idx - 1][0].lower()
    debuglog.info("Country changed to %s" % code)
    addon().setSetting("country", code)
    refresh_playlist(show_notice=True)


# ---- stream tester ---------------------------------------------------------------------

def check_streams(monitor):
    a = addon()
    country = a.getSetting("country")
    try:
        entries = playlist.load_entries(country, a.getSettingBool("dedupe"))
    except Exception as e:
        debuglog.error("Stream test: could not download playlist: %s: %s" % (type(e).__name__, e))
        notify(tr(30102))
        return

    items = streamcheck.load_cache()
    ttl = a.getSettingInt("check_days") * 86400
    todo = [e for e in entries if streamcheck.needs_check(e["url"], items, ttl)]
    debuglog.info("Stream test started: country=%s, %d channels, %d need testing" % (
        country, len(entries), len(todo)))
    if not todo:
        notify(tr(30112).format(len(entries)))
        return

    dlg = xbmcgui.DialogProgress()
    dlg.create(tr(30110), "")

    def progress(done, total, alive, dead):
        dlg.update(int(done * 100 / total), tr(30111).format(done, total, alive, dead))
        return dlg.iscanceled() or monitor.abortRequested()

    t0 = time.time()
    results, cancelled = streamcheck.run(todo, progress)
    dlg.close()

    checked = len(results)
    alive = sum(1 for r in results.values() if r[0])
    dead = checked - alive
    took = time.time() - t0

    # Offline protection: if (almost) nothing answered we assume the PC has no internet.
    if checked >= 20 and alive / checked < 0.03:
        debuglog.warn("Stream test: only %d of %d answered - looks like no internet. Results discarded." % (
            alive, checked))
        notify(tr(30114))
        return

    names = {e["url"]: e["name"] for e in todo}
    now = time.time()
    for url, (ok, reason, ms) in results.items():
        items[url] = [1 if ok else 0, now, reason]
        if not ok:
            debuglog.debug("DEAD  %s | %s | %s (%d ms)" % (names.get(url, "?"), url, reason, ms))
    streamcheck.save_cache(items)

    reasons = Counter(r[1] for r in results.values() if not r[0])
    debuglog.info("Stream test %s: %d checked in %.0fs, %d alive, %d dead. Dead reasons: %s" % (
        "CANCELLED" if cancelled else "finished", checked, took, alive, dead,
        ", ".join("%s x%d" % kv for kv in reasons.most_common()) or "none"))

    kept = refresh_playlist()
    if cancelled:
        notify(tr(30115))
    else:
        notify(tr(30113).format(alive, dead, kept))
    if kept and xbmcgui.Dialog().yesno(ADDON_NAME, tr(30116)):
        pvr_setup.reload_client(monitor)


# ---- diagnostics / logs ----------------------------------------------------------------

def _kodi_log_excerpt(max_lines=300):
    """Lines from kodi.log that mention us or IPTV Simple (stream errors, demuxer failures...)."""
    try:
        path = xbmcvfs.translatePath("special://logpath/kodi.log")
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 3 * 1024 * 1024))
            text = f.read().decode("utf-8", errors="replace")
        keys = ("freelivetv", "pvr.iptvsimple", "CVideoPlayer::OpenDemuxStream", "Playback failed")
        lines = [l for l in text.splitlines() if any(k in l for k in keys)]
        return "\n".join(lines[-max_lines:]) or "(no matching lines)"
    except Exception as e:
        return "(could not read kodi.log: %s)" % e


def diagnostics():
    a = addon()
    lines = [
        "Free Live TV %s" % a.getAddonInfo("version"),
        "Kodi: %s" % xbmc.getInfoLabel("System.BuildVersion"),
        "OS: %s" % xbmc.getInfoLabel("System.OSVersionInfo"),
        "Settings: country=%s dedupe=%s hide_dead=%s refresh_hours=%s check_days=%s debug=%s" % (
            a.getSetting("country"), a.getSetting("dedupe"), a.getSetting("hide_dead"),
            a.getSetting("refresh_hours"), a.getSetting("check_days"), a.getSetting("debug_enabled")),
    ]
    try:
        lines.append("PVR IPTV Simple: %s" % pvr_setup.describe())
    except Exception as e:
        lines.append("PVR IPTV Simple: could not read (%s)" % e)
    pl = paths.playlist_path()
    if os.path.exists(pl):
        with open(pl, encoding="utf-8", errors="replace") as f:
            n = sum(1 for l in f if l.startswith("#EXTINF"))
        lines.append("Playlist: %d channels, updated %s" % (
            n, time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(pl)))))
    else:
        lines.append("Playlist: missing")
    cache = streamcheck.load_cache()
    dead = len(streamcheck.dead_urls(cache))
    lines.append("Stream test cache: %d alive, %d dead" % (len(cache) - dead, dead))
    return "\n".join(lines)


def full_report():
    return "\n".join([
        "===== DIAGNOSTICS =====", diagnostics(),
        "", "===== FREE LIVE TV LOG =====", debuglog.read(),
        "", "===== RELEVANT KODI.LOG LINES =====", _kodi_log_excerpt(),
    ])


def view_log():
    xbmcgui.Dialog().textviewer(tr(30120), full_report())


def export_log():
    dest = xbmcgui.Dialog().browse(3, tr(30118), "files")
    if not dest:
        return
    out = dest + "freelivetv-log-%s.txt" % time.strftime("%Y%m%d-%H%M%S")
    f = xbmcvfs.File(out, "w")
    try:
        f.write(full_report())
    finally:
        f.close()
    debuglog.info("Log exported to %s" % out)
    notify(tr(30117).format(out))


def toggle_kodi_debug():
    """Flip Kodi's own debug logging (needed to see HTTP details from IPTV Simple)."""
    q = '{"jsonrpc":"2.0","id":1,"method":"Settings.GetSettingValue","params":{"setting":"debug.showloginfo"}}'
    import json
    current = json.loads(xbmc.executeJSONRPC(q)).get("result", {}).get("value", False)
    new = not current
    xbmc.executeJSONRPC(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "Settings.SetSettingValue",
        "params": {"setting": "debug.showloginfo", "value": new}}))
    debuglog.info("Kodi debug logging set to %s" % new)
    notify(tr(30119).format("ON" if new else "OFF"))
