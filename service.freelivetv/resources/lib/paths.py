"""All file locations in one place. FLTV_PROFILE env var overrides (used for local tests)."""
import os

from resources.lib.constants import ADDON_ID

_profile = None


def profile_dir():
    global _profile
    if _profile is None:
        override = os.environ.get("FLTV_PROFILE")
        if override:
            _profile = override
        else:
            import xbmcaddon
            import xbmcvfs
            _profile = xbmcvfs.translatePath(xbmcaddon.Addon(ADDON_ID).getAddonInfo("profile"))
    os.makedirs(_profile, exist_ok=True)
    return _profile


def playlist_path():
    return os.path.join(profile_dir(), "playlist.m3u")


def flag_path():
    return os.path.join(profile_dir(), "setup.flag")


def cache_path():
    return os.path.join(profile_dir(), "stream_check.json")


def log_path():
    return os.path.join(profile_dir(), "freelivetv.log")
