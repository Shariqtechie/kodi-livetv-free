#!/usr/bin/env python3
"""Build the Kodi repository site: zips + addons.xml + addons.xml.md5 + landing page.

Usage: python3 scripts/build_repo.py --out site --base-url https://user.github.io/repo/ [--version 0.1.1]
"""
import argparse
import hashlib
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_ADDON = "service.freelivetv"
REPO_ADDON = "repository.freelivetv"


def stage(addon_id, tmp, base_url, version):
    dst = tmp / addon_id
    shutil.copytree(ROOT / addon_id, dst,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    xml_file = dst / "addon.xml"
    text = xml_file.read_text("utf-8").replace("__BASE_URL__", base_url)
    if version and addon_id == MAIN_ADDON:
        text = re.sub(r'(<addon\b[^>]*\bversion=")[^"]*(")',
                      lambda m: m.group(1) + version + m.group(2), text, count=1)
    xml_file.write_text(text, "utf-8")
    return dst


def make_zip(src_dir, addon_id, version, out_dir):
    target = out_dir / addon_id
    target.mkdir(parents=True, exist_ok=True)
    zip_path = target / f"{addon_id}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                z.write(f, Path(addon_id) / f.relative_to(src_dir))
    for asset in ("icon.png", "fanart.png"):
        if (src_dir / asset).exists():
            shutil.copy(src_dir / asset, target / asset)
    return zip_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--version", default="")
    args = ap.parse_args()

    base_url = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    entries, versions = [], {}
    with tempfile.TemporaryDirectory() as t:
        for addon_id in (MAIN_ADDON, REPO_ADDON):
            staged = stage(addon_id, Path(t), base_url, args.version)
            version = ET.parse(staged / "addon.xml").getroot().get("version")
            versions[addon_id] = version
            zp = make_zip(staged, addon_id, version, out)
            if addon_id == REPO_ADDON:
                shutil.copy(zp, out / zp.name)  # convenient top-level download
            text = (staged / "addon.xml").read_text("utf-8")
            entries.append(re.sub(r"^<\?xml[^>]*\?>\s*", "", text).strip())

    addons_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
                  + "\n".join(entries) + "\n</addons>\n")
    (out / "addons.xml").write_text(addons_xml, "utf-8")
    (out / "addons.xml.md5").write_text(
        hashlib.md5(addons_xml.encode("utf-8")).hexdigest(), "utf-8")

    repo_zip = f"{REPO_ADDON}-{versions[REPO_ADDON]}.zip"
    (out / "index.html").write_text(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Free Live TV for Kodi</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;line-height:1.6}}
code{{background:#eee;padding:2px 6px;border-radius:4px}}</style></head><body>
<h1>Free Live TV for Kodi</h1>
<p>Latest: <b>v{versions[MAIN_ADDON]}</b></p>
<p><a href="{repo_zip}">Download {repo_zip}</a></p>
<h2>Install</h2><ol>
<li>Kodi: Settings &rarr; File manager &rarr; Add source &rarr; <code>{base_url}</code> (name it <code>freelivetv</code>)</li>
<li>Settings &rarr; Add-ons &rarr; Install from zip file &rarr; freelivetv &rarr; <code>{repo_zip}</code></li>
<li>Install from repository &rarr; Free Live TV Repository &rarr; Services &rarr; Free Live TV</li></ol>
<p>Updates then arrive automatically. Not affiliated with iptv-org.</p>
</body></html>
""", "utf-8")
    print("Built:", ", ".join(f"{k} {v}" for k, v in versions.items()))


if __name__ == "__main__":
    main()
