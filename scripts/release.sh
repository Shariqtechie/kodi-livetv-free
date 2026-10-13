#!/usr/bin/env bash
# Usage: scripts/release.sh 0.1.1
# Bumps the addon version, commits, tags and pushes. GitHub Actions does the rest.
set -euo pipefail
V="${1:?usage: release.sh X.Y.Z}"
cd "$(dirname "$0")/.."
python3 - "$V" <<'PY'
import re, sys
p = "service.freelivetv/addon.xml"
t = open(p, encoding="utf-8").read()
t = re.sub(r'(<addon\b[^>]*\bversion=")[^"]*(")', lambda m: m.group(1) + sys.argv[1] + m.group(2), t, count=1)
open(p, "w", encoding="utf-8").write(t)
PY
git add -A
git commit -m "Release v$V"
git tag "v$V"
git push origin HEAD "v$V"
echo "Pushed v$V - watch the Actions tab."
