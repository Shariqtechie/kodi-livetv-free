#!/usr/bin/env bash
# Usage: scripts/release.sh 0.1.1
set -euo pipefail
V="${1:?usage: release.sh X.Y.Z}"
cd "$(dirname "$0")/.."

# only touch the <addon ...> line, not the <?xml version="1.0"?> line
sed -i -E '/<addon /s/(version=")[^"]*(")/\1'"$V"'\2/' service.freelivetv/addon.xml

git add -A
git diff --cached --quiet || git commit -m "Release v$V"
git tag "v$V"
git push origin HEAD "v$V"
echo "Pushed v$V - watch the Actions tab."