"""Install PVR IPTV Simple Client and point it at our playlist.

Kodi 20.8+ keeps IPTV Simple settings in instance-settings-N.xml files that Python's
setSetting() cannot reach, so we edit/write the XML while the client is disabled.
Technique adapted from the JioTV Direct add-on (MIT). We only ever touch OUR instance.
"""
import json
import os
import re
from xml.sax.saxutils import escape

import xbmc
import xbmcvfs

from resources.lib import debuglog
from resources.lib.constants import ADDON_ID, ADDON_NAME, PVR_ID

_INSTANCE_RE = re.compile(r"instance-settings-(\d+)\.xml$")


def _rpc(method, params):
    q = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    return json.loads(xbmc.executeJSONRPC(q))


def _pvr_enabled_state():
    """None = not installed, else True/False for enabled."""
    r = _rpc("Addons.GetAddonDetails", {"addonid": PVR_ID, "properties": ["enabled"]})
    addon = r.get("result", {}).get("addon")
    return None if not addon else addon.get("enabled")


def _set_enabled(flag):
    _rpc("Addons.SetAddonEnabled", {"addonid": PVR_ID, "enabled": flag})


def ensure_installed(monitor):
    if _pvr_enabled_state() is not None:
        return True
    debuglog.info("PVR: %s not installed, requesting install" % PVR_ID)
    xbmc.executebuiltin("InstallAddon(%s)" % PVR_ID, True)
    for _ in range(60):  # wait up to a minute for the user to confirm + download
        if _pvr_enabled_state() is not None:
            return True
        if monitor.waitForAbort(1):
            return False
    return False


def _pvr_profile_dir():
    path = xbmcvfs.translatePath("special://profile/addon_data/%s/" % PVR_ID)
    os.makedirs(path, exist_ok=True)
    return path


def _render(values):
    lines = ['<settings version="2">']
    for key, val in values.items():
        lines.append('    <setting id="%s">%s</setting>' % (key, escape(str(val))))
    lines.append("</settings>\n")
    return "\n".join(lines)


def _set_value(xml, key, value):
    pattern = re.compile(r'<setting id="%s"[^>]*?(?:/>|>.*?</setting>)' % re.escape(key), re.S)
    new = '<setting id="%s">%s</setting>' % (key, escape(str(value)))
    if pattern.search(xml):
        return pattern.sub(lambda _m: new, xml, count=1)
    return xml.replace("</settings>", "    %s\n</settings>" % new)


def _remove_value(xml, key):
    pattern = re.compile(r'[ \t]*<setting id="%s"[^>]*?(?:/>|>.*?</setting>)\n?' % re.escape(key), re.S)
    return pattern.sub("", xml)


def configure(m3u_path, refresh_minutes, monitor):
    """Create or update OUR IPTV Simple instance. Other instances are never touched."""
    values = {
        "kodi_addon_instance_name": ADDON_NAME,
        "kodi_addon_instance_enabled": "true",
        "m3uPathType": "0",
        "m3uPath": m3u_path,
        "m3uRefreshMode": "1",
        "epgPathType": "1",
        "epgUrl": "",
    }
    debuglog.debug("PVR: configuring with %s" % values)
    _set_enabled(False)
    monitor.waitForAbort(1)

    d = _pvr_profile_dir()
    files = [f for f in os.listdir(d) if _INSTANCE_RE.match(f)]
    ours = None
    for f in files:
        with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
            if ADDON_ID in fh.read():
                ours = f
                break

    if ours:
        path = os.path.join(d, ours)
        with open(path, encoding="utf-8") as fh:
            xml = fh.read()
        for k, v in values.items():
            xml = _set_value(xml, k, v)
        # v0.2.0 wrote a value IPTV Simple rejects ("failed to load value 720") - remove it
        xml = _remove_value(xml, "m3uRefreshIntervalMins")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        debuglog.info("PVR: updated our instance file %s" % ours)
    else:
        used = {int(_INSTANCE_RE.match(f).group(1)) for f in files}
        n = next(i for i in range(1, 1000) if i not in used)
        path = os.path.join(d, "instance-settings-%d.xml" % n)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_render(values))
        debuglog.info("PVR: created new instance file %s" % path)

    _set_enabled(True)
    return True


def reload_client(monitor):
    """Disable/enable IPTV Simple so it re-reads the playlist file."""
    debuglog.info("PVR: reloading client")
    _set_enabled(False)
    monitor.waitForAbort(2)
    _set_enabled(True)


def describe():
    """One-line status for diagnostics: version, enabled, instance files."""
    r = _rpc("Addons.GetAddonDetails", {"addonid": PVR_ID, "properties": ["enabled", "version"]})
    addon = r.get("result", {}).get("addon")
    if not addon:
        return "not installed"
    parts = ["v%s" % addon.get("version"), "enabled" if addon.get("enabled") else "DISABLED"]
    d = _pvr_profile_dir()
    for f in sorted(os.listdir(d)):
        if _INSTANCE_RE.match(f):
            with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                parts.append(f + (" (ours)" if ADDON_ID in fh.read() else ""))
    return ", ".join(parts)
