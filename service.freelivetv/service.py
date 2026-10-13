import os
import time

import xbmc
import xbmcgui

from resources.lib import core, debuglog
from resources.lib.constants import ADDON_NAME


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

    # First run: wait for Kodi to settle, then offer one-click setup.
    if not os.path.exists(core.flag_path()):
        if monitor.waitForAbort(10):
            return
        if xbmcgui.Dialog().yesno(ADDON_NAME, core.tr(30100)):
            core.setup(monitor)
        else:
            debuglog.info("User declined first-run setup")
            with open(core.flag_path(), "w") as f:
                f.write("declined")  # don't nag; user can run it from settings

    while not monitor.abortRequested():
        path = core.playlist_path()
        max_age = core.addon().getSettingInt("refresh_hours") * 3600
        stale = not os.path.exists(path) or time.time() - os.path.getmtime(path) > max_age
        if monitor.changed or stale:
            debuglog.debug("Refresh triggered (settings changed=%s, stale=%s)" % (monitor.changed, stale))
            monitor.changed = False
            core.refresh_playlist()
        if monitor.waitForAbort(60):
            break
    debuglog.info("Service stopped")


main()
