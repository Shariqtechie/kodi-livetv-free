import sys
import traceback

import xbmc

from resources.lib import core, debuglog

action = sys.argv[1] if len(sys.argv) > 1 else "setup"
monitor = xbmc.Monitor()
debuglog.debug("script action: %s" % action)

try:
    if action == "setup":
        core.setup(monitor)
    elif action == "refresh":
        core.refresh_playlist(show_notice=True)
    elif action == "choose_country":
        core.choose_country()
    elif action == "check_streams":
        core.check_streams(monitor)
    elif action == "view_log":
        core.view_log()
    elif action == "export_log":
        core.export_log()
    elif action == "toggle_kodi_debug":
        core.toggle_kodi_debug()
except Exception as e:  # make sure ANY crash lands in our log with its full message
    debuglog.error("Action '%s' crashed: %s: %s" % (action, type(e).__name__, e))
    debuglog.error(traceback.format_exc())
    core.notify("Error - see Troubleshooting > View log")
