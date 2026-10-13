import sys

import xbmc

from resources.lib import core

action = sys.argv[1] if len(sys.argv) > 1 else "setup"
monitor = xbmc.Monitor()

if action == "setup":
    core.setup(monitor)
elif action == "refresh":
    core.refresh_playlist(show_notice=True)
elif action == "choose_country":
    core.choose_country()
