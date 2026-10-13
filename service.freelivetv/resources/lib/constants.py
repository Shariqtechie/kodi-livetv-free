ADDON_ID = "service.freelivetv"
ADDON_NAME = "Free Live TV"
PVR_ID = "pvr.iptvsimple"

BASE_URL = "https://iptv-org.github.io/iptv"
COUNTRIES_API = "https://iptv-org.github.io/api/countries.json"
USER_AGENT = "Kodi-FreeLiveTV/0.2"

# Stream tester
DEFAULT_UA = "Mozilla/5.0"      # same UA IPTV Simple used for iptv-org entries
CHECK_TIMEOUT = 8               # seconds per stream
CHECK_WORKERS = 20              # parallel checks

# Own log file (kept small; rotated to .1)
LOG_MAX_BYTES = 512 * 1024
