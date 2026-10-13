# Free Live TV for Kodi

Free live TV from any country, set up in one click. Pulls public playlists from
[iptv-org/iptv](https://github.com/iptv-org/iptv), cleans them, and auto-configures
**PVR IPTV Simple Client**. Not affiliated with iptv-org. Hosts no content, only links.

## Install (users)
1. Kodi → Settings → File manager → Add source → `https://<user>.github.io/<repo>/`
2. Settings → Add-ons → Install from zip file → pick `repository.freelivetv-1.0.0.zip`
3. Install from repository → Free Live TV Repository → Services → **Free Live TV**
4. Say **Yes** to the setup prompt, then open **TV** on the home screen.

Change country any time: Add-on settings → *Pick country from list*.

## Release (maintainers)
```
scripts/release.sh 0.1.1
```
That bumps the version, commits, tags `v0.1.1` and pushes. GitHub Actions builds the zips +
`addons.xml` and publishes them to GitHub Pages; every installed Kodi picks it up on its next
repo check. One-time GitHub setup: **Settings → Pages → Source: GitHub Actions**.

## Credits
iptv-org community for the playlists. The IPTV Simple instance-settings technique is adapted from
the JioTV Direct add-on (MIT).
