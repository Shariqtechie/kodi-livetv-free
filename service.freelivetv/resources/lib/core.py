import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import playlist, pvr_setup
from resources.lib.constants import ADDON_ID, ADDON_NAME


def addon():
    return xbmcaddon.Addon(ADDON_ID)


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, msg), level)


def tr(string_id):
    return addon().getLocalizedString(string_id)


def notify(msg):
    xbmcgui.Dialog().notification(ADDON_NAME, msg, xbmcgui.NOTIFICATION_INFO, 4000)


def profile_dir():
    path = xbmcvfs.translatePath(addon().getAddonInfo("profile"))
    os.makedirs(path, exist_ok=True)
    return path


def playlist_path():
    return os.path.join(profile_dir(), "playlist.m3u")


def flag_path():
    return os.path.join(profile_dir(), "setup.flag")


def refresh_playlist(show_notice=False):
    a = addon()
    try:
        count = playlist.generate(
            a.getSetting("country"), playlist_path(), a.getSettingBool("dedupe")
        )
    except Exception as e:  # network down, bad country code, empty list...
        log("Playlist refresh failed: %s" % e, xbmc.LOGWARNING)
        if show_notice:
            notify(tr(30102))
        return False
    log("Playlist updated: %d channels" % count)
    if show_notice:
        notify(tr(30101).format(count))
    return True


def setup(monitor):
    """Refresh playlist, install IPTV Simple if missing, configure it."""
    if not refresh_playlist(show_notice=True) and not os.path.exists(playlist_path()):
        return False
    if not pvr_setup.ensure_installed(monitor):
        notify(tr(30104))
        return False
    minutes = addon().getSettingInt("refresh_hours") * 60
    pvr_setup.configure(playlist_path(), minutes, monitor)
    with open(flag_path(), "w") as f:
        f.write("done")
    notify(tr(30103))
    return True


def choose_country():
    try:
        countries = playlist.list_countries()
    except Exception as e:
        log("Country list failed: %s" % e, xbmc.LOGWARNING)
        notify(tr(30102))
        return
    labels = [tr(30106)] + ["%s (%s)" % (name, code) for code, name in countries]
    idx = xbmcgui.Dialog().select(tr(30105), labels)
    if idx < 0:
        return
    code = "all" if idx == 0 else countries[idx - 1][0].lower()
    addon().setSetting("country", code)
    refresh_playlist(show_notice=True)
