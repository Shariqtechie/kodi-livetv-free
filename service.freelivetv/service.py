import os
import time
import traceback

import xbmc

from resources.lib import core, debuglog


class SettingsMonitor(xbmc.Monitor):
    changed = False

    def onSettingsChanged(self):
        self.changed = True


def main():
    monitor = SettingsMonitor()
    debuglog.info("Service started")
    try:
        debuglog.info("Diagnostics:\n" + core.diagnostics())
    except Exception as e:
        debuglog.warn("Diagnostics failed: %s" % e)

    if not os.path.exists(core.flag_path()):
        # First run: let Kodi settle, then the welcome flow (country -> setup -> optional test).
        if monitor.waitForAbort(10):
            return
        core.first_run(monitor)
    elif not core.has_signature():
        core.refresh_playlist()  # upgraded from an older version: apply new options once

    ticks = 0
    while not monitor.abortRequested():
        if monitor.changed:
            monitor.changed = False
            # Only react to settings that change the playlist (country, dedupe, hide dead, merge).
            if core.signature_changed():
                debuglog.debug("Playlist-relevant setting changed")
                if core.refresh_playlist(show_notice=True):
                    core.offer_reload(monitor)
        elif ticks % 12 == 0:  # about once a minute
            path = core.playlist_path()
            max_age = core.addon().getSettingInt("refresh_hours") * 3600
            if not os.path.exists(path) or time.time() - os.path.getmtime(path) > max_age:
                debuglog.debug("Playlist is stale, refreshing")
                core.refresh_playlist()
        ticks += 1
        if monitor.waitForAbort(5):
            break
    debuglog.info("Service stopped")


try:
    main()
except Exception as e:
    debuglog.error("Service crashed: %s: %s" % (type(e).__name__, e))
    debuglog.error(traceback.format_exc())
