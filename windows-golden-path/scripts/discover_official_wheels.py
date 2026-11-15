# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Discover official AMD Windows wheel candidates (mission §4) — R22-ready.

Scans each official channel SEPARATELY (multi-arch / stable / rc / nightly /
dev), parses real index HTML, and NEVER synthesizes a wheel URL: every entry
in the output was an href observed on the channel's own index page.

Outputs (under --out-dir):
  wheel_discovery.json   raw per-channel package/version inventory + errors
  candidate_matrix.json  Windows win_amd64 candidates per package per channel

Exit 0 = scan completed (even if some channels are down — recorded honestly).
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (WindowsGoldenPath/1.0; +https://github.com/AIwork4me)"}
CTX = ssl.create_default_context()  # repo.amd.com serves valid TLS


def fetch(url: str, timeout: int = 90) -> tuple[int, str, str | None]:
    """GET with explicit status/error recording (no silent retries)."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.getcode(), r.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return e.code, "", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 — DNS/TLS failures are channel facts
        return 0, "", f"{type(e).__name__}: {e}"


def parse_index_hrefs(html: str) -> list[str]:
    """Extract href targets from a PEP 503-style simple index page."""
    return re.findall(r'href=["\']([^"\']+)["\']', html)


def scan_channel(name: str, base: str, packages: list[str]) -> dict:
    """Scan one channel: root page first (layout probe), then package pages.

    Layouts observed in P14/P16:
      multi-arch: root page lists wheel hrefs directly per package dir /torch/
      whl-next:   root lists package dirs, each dir is a simple index
    """
    ch: dict = {"channel": name, "base_url": base, "packages": {}, "errors": []}
    code, html, err = fetch(base)
    ch["root_status"] = code
    if err:
        ch["errors"].append({"url": base, "error": err})
        return ch
    root_hrefs = parse_index_hrefs(html)
    ch["root_hrefs_sample"] = root_hrefs[:50]

    for pkg in packages:
        pkg_entry: dict = {"windows_wheels": [], "other_wheels_count": 0, "status": None}
        # candidate index URLs: root itself (multi-arch flat layout), root+pkg,
        # and root+pkg with underscores (PEP 503 normalizes dashes)
        tried = []
        for url in (base, f"{base}{pkg}/", f"{base}{pkg.replace('-', '_')}/"):
            code, ph, err = fetch(url)
            tried.append(url)
            if err or code != 200 or not ph:
                continue
            hrefs = parse_index_hrefs(ph)
            wheels = [h.rsplit("/", 1)[-1] for h in hrefs if h.endswith(".whl")]
            if not wheels:
                continue
            for fn in wheels:
                parsed = gp_lib.parse_wheel_filename(fn)
                if not parsed:
                    continue
                if parsed["win_amd64"]:
                    # wheel hrefs on AMD simple-index pages are relative filenames
                    pkg_entry["windows_wheels"].append({
                        "filename": fn, "version": parsed["version"],
                        "python_tag": parsed["python_tag"],
                        "page_url": url,
                        "wheel_url": url + fn,
                    })
                else:
                    pkg_entry["other_wheels_count"] += 1
            if pkg_entry["windows_wheels"] or pkg_entry["other_wheels_count"]:
                pkg_entry["status"] = "ok"
                break
        if pkg_entry["status"] is None:
            pkg_entry["status"] = "not_listed"
            pkg_entry["tried_urls"] = tried
        ch["packages"][pkg] = pkg_entry
    return ch


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--channels", default=",".join(gp_lib.OFFICIAL_CHANNELS),
                    help="comma-separated channel names (default: all five)")
    ap.add_argument("--gfx", default="gfx1100",
                    help="architecture focus for candidate matrix ordering")
    args = ap.parse_args()

    stamp = datetime.now(tz=timezone.utc).isoformat()
    discovery = {"run_id": f"R21-WHEEL-DISCOVERY-{stamp[:10]}", "scanned_utc": stamp,
                 "gfx_focus": args.gfx, "channels": {}}
    for ch_name in [c.strip() for c in args.channels.split(",") if c.strip()]:
        base = gp_lib.OFFICIAL_CHANNELS[ch_name]
        print(f"[scan] {ch_name}: {base}", flush=True)
        discovery["channels"][ch_name] = scan_channel(ch_name, base, gp_lib.DISCOVERY_PACKAGES)
        n = sum(len(p["windows_wheels"]) for p in discovery["channels"][ch_name]["packages"].values())
        print(f"[scan] {ch_name}: {n} windows wheels across "
              f"{len(gp_lib.DISCOVERY_PACKAGES)} packages", flush=True)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "wheel_discovery.json").write_text(
        json.dumps(discovery, indent=2, ensure_ascii=False), encoding="utf-8")

    # candidate matrix: newest Windows wheel per package per channel
    matrix = {"scanned_utc": stamp, "gfx_focus": args.gfx, "channels": {}}
    for ch_name, ch in discovery["channels"].items():
        rows = {}
        for pkg, entry in ch["packages"].items():
            wins = entry["windows_wheels"]
            if wins:
                newest = sorted(wins, key=lambda w: w["version"])[-1]
                rows[pkg] = {"newest_version": newest["version"],
                             "filename": newest["filename"], "python_tag": newest["python_tag"],
                             "page_url": newest["page_url"],
                             "n_win_wheels": len(wins),
                             "all_win_versions": sorted({w["version"] for w in wins})}
            else:
                rows[pkg] = {"newest_version": None, "status": entry["status"]}
        matrix["channels"][ch_name] = {"root_status": ch["root_status"], "packages": rows}
    (out_dir / "candidate_matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] wrote {out_dir/'wheel_discovery.json'} and candidate_matrix.json")


if __name__ == "__main__":
    main()
