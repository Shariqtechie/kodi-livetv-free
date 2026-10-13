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


INDEX_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Free Live TV for Kodi</title>
<meta name="description" content="Free live TV from any country in Kodi. Pick your country, press OK, done. Open source, no accounts, updates itself.">
<meta property="og:type" content="website">
<meta property="og:title" content="Free Live TV for Kodi">
<meta property="og:description" content="Free live TV from any country in Kodi. Pick your country, press OK, done. Dead streams hidden, updates itself.">
<meta property="og:image" content="{{BASE_URL}}banner.png">
<meta property="og:url" content="{{BASE_URL}}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="service.freelivetv/icon.png">
<style>
:root{--bg:#f4f8fb;--card:#fff;--text:#0d1b2a;--muted:#55677a;--border:#dde7ee;--accent:#0096aa;--accent-d:#0b6b7a;--code:#eaf2f6;--shadow:0 6px 24px rgba(10,30,60,.07)}
@media (prefers-color-scheme:dark){:root{--bg:#07111d;--card:#0e1c2c;--text:#e7f0f5;--muted:#9bb0c1;--border:#1b2e42;--accent:#2cc4d8;--accent-d:#7fe0ee;--code:#142638;--shadow:0 6px 24px rgba(0,0,0,.35)}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent-d)}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:8px}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
.hero{background:linear-gradient(135deg,#0a1642 0%,#0b4f7a 55%,#008ca5 100%);color:#fff;padding:64px 0 76px;text-align:center;position:relative;overflow:hidden}
.hero::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 80% 20%,rgba(255,255,255,.12),transparent 45%),radial-gradient(circle at 10% 90%,rgba(255,255,255,.08),transparent 40%)}
.hero .wrap{position:relative}
.hero img.logo{width:104px;height:104px;border-radius:24px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
.pill{display:inline-block;margin-top:18px;padding:4px 14px;border-radius:999px;background:rgba(255,255,255,.16);font-size:.85rem;font-weight:600;letter-spacing:.02em}
h1{font-size:clamp(2.1rem,6vw,3.4rem);line-height:1.1;margin:14px 0 10px;font-weight:800}
.tag{font-size:clamp(1.05rem,2.6vw,1.3rem);max-width:640px;margin:0 auto;color:#dff3f8}
.sub{margin-top:8px;font-size:.95rem;color:#b9dde6}
.btns{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:30px}
.btn{display:inline-block;padding:13px 24px;border-radius:12px;font-weight:700;text-decoration:none;font-size:1rem;transition:transform .15s,box-shadow .15s}
.btn:hover{transform:translateY(-2px)}
.btn.primary{background:#fff;color:#08306b;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.btn.ghost{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.35)}
section{padding:56px 0 8px}
h2{font-size:1.7rem;margin:0 0 6px;text-align:center}
.lead{text-align:center;color:var(--muted);margin:0 auto 30px;max-width:620px}
.steps{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));counter-reset:s}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px;box-shadow:var(--shadow)}
.step{position:relative;padding-top:54px}
.step::before{counter-increment:s;content:counter(s);position:absolute;top:16px;left:20px;width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;font-weight:800;display:grid;place-items:center}
.card h3{margin:0 0 6px;font-size:1.05rem}
.card p{margin:0;color:var(--muted);font-size:.95rem}
code,.src{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:var(--code);padding:2px 6px;border-radius:6px;font-size:.88em}
.copybox{display:flex;gap:8px;align-items:stretch;margin-top:10px}
.src{flex:1;min-width:0;background:var(--code);border-radius:10px;padding:9px 11px;font-size:.78rem;overflow-wrap:anywhere}
.copy{border:0;border-radius:10px;padding:0 14px;background:var(--accent);color:#fff;font-weight:700;cursor:pointer}
.note{margin:22px auto 0;max-width:760px;padding:14px 18px;border-left:4px solid var(--accent);background:var(--card);border-radius:8px;color:var(--muted);font-size:.93rem}
.stats{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-top:6px}
.stat{text-align:center}
.stat b{display:block;font-size:2.2rem;color:var(--accent);line-height:1.1}
.stat span{color:var(--muted);font-size:.9rem}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.ico{font-size:1.6rem;margin-bottom:8px}
.shots{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 16px;scroll-snap-type:x mandatory}
.shots img{height:300px;border-radius:12px;border:1px solid var(--border);scroll-snap-align:start;flex:none}
details{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 18px;margin-bottom:10px}
summary{cursor:pointer;font-weight:700}
details p{margin:10px 0 2px;color:var(--muted)}
.kodi{margin-top:56px;background:var(--card);border:1px dashed var(--border);border-radius:16px;padding:22px}
.kodi h2{text-align:left;font-size:1.15rem}
.kodi p{color:var(--muted);margin:4px 0 12px;font-size:.92rem}
.kodi ul{margin:0;padding-left:20px}
footer{padding:44px 0 56px;text-align:center;color:var(--muted);font-size:.9rem}
footer p{max-width:700px;margin:6px auto}
@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
</style>
</head>
<body>

<header class="hero">
<div class="wrap">
<img class="logo" src="service.freelivetv/icon.png" alt="Free Live TV logo">
<div><span class="pill">Latest version v{{VERSION}}</span></div>
<h1>Free Live TV for Kodi</h1>
<p class="tag">Live TV from any country. Pick yours, press OK, start watching.</p>
<p class="sub">Open source. No accounts. No ads. Updates itself.</p>
<div class="btns">
<a class="btn primary" href="{{REPO_ZIP}}">Download repository zip</a>
<a class="btn ghost" href="{{GITHUB}}">Star on GitHub</a>
<a class="btn ghost" href="{{GITHUB}}/releases">Releases</a>
</div>
</div>
</header>

<main class="wrap">

<section id="install">
<h2>Install in 2 minutes</h2>
<p class="lead">Install the repository once and Kodi keeps the add-on up to date for you.</p>
<div class="steps">
<div class="card step">
<h3>Add the source</h3>
<p>Kodi: Settings, File manager, Add source. Enter this address and name it <code>freelivetv</code>.</p>
<div class="copybox"><div class="src" id="srcurl">{{BASE_URL}}</div><button class="copy" type="button" onclick="copyText('srcurl',this)">Copy</button></div>
</div>
<div class="card step">
<h3>Install the repository</h3>
<p>Settings, Add-ons, Install from zip file, <code>freelivetv</code>, then pick <code>{{REPO_ZIP}}</code>.</p>
</div>
<div class="card step">
<h3>Install Free Live TV</h3>
<p>Install from repository, Free Live TV Repository, then install <b>Free Live TV</b>.</p>
</div>
<div class="card step">
<h3>Pick your country</h3>
<p>A picker appears after a few seconds. India is preselected, so just press OK. Then open <b>TV</b> on the home screen.</p>
</div>
</div>
<div class="note"><b>Tip:</b> if Kodi shows an error or crashes while installing PVR IPTV Simple Client (it happens occasionally), restart Kodi, open the add-on's settings, go to the Tools tab and press <b>Set up / repair Live TV now</b>.</div>
</section>

<section>
<h2>Why not set it up by hand?</h2>
<p class="lead">Because half of any free channel list is dead, and nobody enjoys clicking through them.</p>
<div class="card">
<div class="stats">
<div class="stat"><b>772</b><span>channels tested in India's list</span></div>
<div class="stat"><b>83</b><span>were dead (11%)</span></div>
<div class="stat"><b>45 s</b><span>to find and hide them all</span></div>
</div>
</div>
</section>

<section>
<h2>What you get</h2>
<p class="lead">Everything runs inside Kodi's own TV menu. No extra apps.</p>
<div class="grid">
<div class="card"><div class="ico">&#9889;</div><h3>One-click setup</h3><p>Installs and configures PVR IPTV Simple Client for you. Your existing PVR setup is never touched.</p></div>
<div class="card"><div class="ico">&#127757;</div><h3>Every country</h3><p>All the countries the iptv-org project covers, plus an "All countries" option. Switch any time.</p></div>
<div class="card"><div class="ico">&#9989;</div><h3>Dead streams hidden</h3><p>One button tests every stream and hides the ones that don't answer. Revived streams come back on the next test.</p></div>
<div class="card"><div class="ico">&#129529;</div><h3>No duplicate clutter</h3><p>Channel listed five times? Only the best working stream stays.</p></div>
<div class="card"><div class="ico">&#128260;</div><h3>Updates itself</h3><p>The repository keeps the add-on current, and the playlist refreshes on a schedule you choose.</p></div>
<div class="card"><div class="ico">&#128295;</div><h3>Built-in troubleshooting</h3><p>Debug log, log viewer and a one-click export with everything needed to report a problem.</p></div>
</div>
</section>

{{SHOTS}}

<section>
<h2>Questions</h2>
<p class="lead">&nbsp;</p>
<details><summary>Which devices does it work on?</summary><p>Tested and working on Windows, Android TV and Android phones, on Kodi 21 (Omega). Linux, macOS and Raspberry Pi should work too but haven't been confirmed yet.</p></details>
<details><summary>Some channels won't play. Is it broken?</summary><p>Public streams come and go, and some are blocked outside their home country. Run "Test channels now" in the add-on settings to hide the dead ones. The test checks that a stream answers, not how smoothly it plays, so a few may still buffer.</p></details>
<details><summary>Does it have a TV guide (EPG)?</summary><p>Not yet. It's on the roadmap as an optional feature.</p></details>
<details><summary>Is this legal?</summary><p>The add-on hosts no content. It only links to publicly available streams listed by the iptv-org project. Availability and licensing vary by country and channel, and you're responsible for how you use it.</p></details>
<details><summary>Something broke. What do I send?</summary><p>Open the add-on settings, Troubleshooting, then "Export log to folder", and attach the file to a new issue on GitHub. It contains versions, settings and the relevant log lines.</p></details>
</section>

<section class="kodi" id="kodi-files">
<h2>Files for Kodi</h2>
<p>This list is what Kodi reads when you add this page as a source. You normally don't need to click these yourself.</p>
<ul>
<li><a href="{{REPO_ZIP}}">{{REPO_ZIP}}</a></li>
<li><a href="addons.xml">addons.xml</a></li>
<li><a href="addons.xml.md5">addons.xml.md5</a></li>
</ul>
</section>

</main>

<footer>
<div class="wrap">
<p>Free Live TV is open source (MIT). Channel lists come from the community-run iptv-org project; this project is independent and not affiliated with it.</p>
<p>It hosts no streams or content. All channel names and trademarks belong to their owners.</p>
<p><a href="{{GITHUB}}">Source on GitHub</a></p>
</div>
</footer>

<script>
function copyText(id,btn){
  var el=document.getElementById(id),text=el.textContent.trim();
  function done(){btn.textContent='Copied!';setTimeout(function(){btn.textContent='Copy'},1600)}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(done,fallback)}else{fallback()}
  function fallback(){var r=document.createRange();r.selectNodeContents(el);var s=window.getSelection();s.removeAllRanges();s.addRange(r);try{document.execCommand('copy');done()}catch(e){}}
}
</script>
</body>
</html>
"""


def github_url(base_url):
    """https://user.github.io/repo/ -> https://github.com/user/repo (fallback: github.com)."""
    m = re.match(r"https://([^./]+)\.github\.io/([^/]+)/?", base_url)
    return "https://github.com/%s/%s" % (m.group(1), m.group(2)) if m else "https://github.com"


def screenshots_html(out):
    """Copy docs/screenshots/* into the site and return a gallery section (or nothing)."""
    src = ROOT / "docs" / "screenshots"
    imgs = sorted(p for p in src.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")) if src.exists() else []
    if not imgs:
        return ""
    (out / "screenshots").mkdir(exist_ok=True)
    tags = []
    for i, img in enumerate(imgs, 1):
        shutil.copy(img, out / "screenshots" / img.name)
        tags.append('<img src="screenshots/%s" alt="Screenshot %d" loading="lazy">' % (img.name, i))
    return ('<section><h2>See it in action</h2><p class="lead">Real screenshots from Kodi.</p>'
            '<div class="shots">%s</div></section>' % "".join(tags))


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
    if (ROOT / "docs" / "banner.png").exists():
        shutil.copy(ROOT / "docs" / "banner.png", out / "banner.png")  # link-preview image
    page = (INDEX_TEMPLATE
            .replace("{{BASE_URL}}", base_url)
            .replace("{{VERSION}}", versions[MAIN_ADDON])
            .replace("{{REPO_ZIP}}", repo_zip)
            .replace("{{GITHUB}}", github_url(base_url))
            .replace("{{SHOTS}}", screenshots_html(out)))
    (out / "index.html").write_text(page, "utf-8")
    print("Built:", ", ".join(f"{k} {v}" for k, v in versions.items()))


if __name__ == "__main__":
    main()
