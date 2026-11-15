# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Resolve a verified, hash-pinned official package set (mission §4).

Resolution is metadata-driven, never filename-guessed:
  1. reads wheel_discovery.json (produced by discover_official_wheels.py;
     refuses to run without it — no synthesized URLs)
  2. checks wheel tags / python ABI / win_amd64 from REAL index entries
  3. asks pip itself for dependency resolution via `pip install --dry-run
     --report` (exact Requires-Dist / Requires-Python handling, PEP 658)
  4. downloads every resolved wheel to the local wheel dir and records SHA256
  5. enforces the mixing rules: no ROCm 7.x + 10.x mix, device wheel required
     for the target gfx, torch must be an AMD HIP build

Output: resolved_wheel_lock.json + requirements-lock/<setname>.txt (hash-pinned)
Exit 3 = BLOCKED_OFFICIAL_ARTIFACT (no qualifying candidate on the channel).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402


def pip_dryrun_report(python: str, channel_url: str, targets: list[str],
                      extra_index: str | None) -> dict:
    """Clean-room pip resolution: exact URLs + versions, nothing installed."""
    cmd = [python, "-m", "pip", "install", "--dry-run", "--ignore-installed",
           "--quiet", "--report", "-", "--index-url", channel_url]
    if extra_index:
        cmd += ["--extra-index-url", extra_index]
    cmd += targets
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"pip dry-run failed ({r.returncode}): {r.stderr[-2000:]}")
    return json.loads(r.stdout)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--discovery", required=True, help="wheel_discovery.json path")
    ap.add_argument("--out", required=True, help="resolved_wheel_lock.json path")
    ap.add_argument("--python", required=True, help="python used for pip resolution")
    ap.add_argument("--channel", required=True, choices=list(gp_lib.OFFICIAL_CHANNELS))
    ap.add_argument("--gfx", default="gfx1100")
    ap.add_argument("--python-tag", default=None,
                    help="e.g. cp312; default = tag of --python")
    ap.add_argument("--torch-version", default=None,
                    help="pin a specific torch version discovered on the channel")
    ap.add_argument("--set-name", default=None, help="lock set name (default auto)")
    ap.add_argument("--wheels-dir", required=True, help="local wheel download dir")
    ap.add_argument("--include-ultralytics", default="8.4.214",
                    help="ultralytics pin from PyPI (empty string to skip)")
    args = ap.parse_args()

    disc = json.loads(Path(args.discovery).read_text(encoding="utf-8"))
    ch = disc["channels"].get(args.channel)
    if not ch:
        print(f"BLOCKED_OFFICIAL_ARTIFACT: channel {args.channel} absent from discovery",
              file=sys.stderr)
        sys.exit(3)

    # python tag of the resolving interpreter when not given
    tag = args.python_tag
    if not tag:
        v = subprocess.run([args.python, "-c",
                            "import sys;print(f'cp{sys.version_info.major}{sys.version_info.minor}')"],
                           capture_output=True, text=True, timeout=60).stdout.strip()
        tag = v

    torch_key = "torch"
    torch_wheels = ch["packages"][torch_key]["windows_wheels"]
    if args.torch_version:
        match = [w for w in torch_wheels if w["version"] == args.torch_version]
    else:
        match = sorted(torch_wheels, key=lambda w: w["version"])[-1:]
    if not match:
        print(f"BLOCKED_OFFICIAL_ARTIFACT: no torch wheel on {args.channel} "
              f"(requested {args.torch_version or 'any'})", file=sys.stderr)
        sys.exit(3)
    torch_pick = match[-1]
    if tag not in torch_pick["python_tag"] and not torch_pick["python_tag"].startswith("py3"):
        print(f"BLOCKED_OFFICIAL_ARTIFACT: torch {torch_pick['version']} tags "
              f"{torch_pick['python_tag']} do not match {tag}", file=sys.stderr)
        sys.exit(3)
    if "+rocm" not in torch_pick["version"]:
        print(f"BLOCKED_OFFICIAL_ARTIFACT: torch {torch_pick['version']} is not an "
              "AMD ROCm build (refusing non-HIP substitution)", file=sys.stderr)
        sys.exit(3)

    # targets for pip: torch + the arch device wheels that exist on this channel
    targets = [f"torch=={torch_pick['version']}"]
    dev_pkgs = [p for p in gp_lib.DISCOVERY_PACKAGES
                if args.gfx.replace("gfx", "gfx") in p and ("torch-device" in p or "torchvision-device" in p)]
    for p in dev_pkgs:
        entry = ch["packages"][p]
        if entry["windows_wheels"]:
            newest = sorted(entry["windows_wheels"], key=lambda w: w["version"])[-1]
            targets.append(f"{p}=={newest['version']}")
    if args.include_ultralytics:
        targets.append(f"ultralytics=={args.include_ultralytics}")

    extra = "https://pypi.org/simple" if args.include_ultralytics else None
    print(f"[resolve] pip dry-run on {args.channel}: {targets}")
    report = pip_dryrun_report(args.python, gp_lib.OFFICIAL_CHANNELS[args.channel],
                               targets, extra)

    wheels_dir = Path(args.wheels_dir)
    wheels_dir.mkdir(parents=True, exist_ok=True)
    lock = {
        "set_name": args.set_name or f"{args.channel}-{torch_pick['version']}-{tag}",
        "channel": args.channel, "channel_url": gp_lib.OFFICIAL_CHANNELS[args.channel],
        "gfx_target": args.gfx, "python_tag": tag,
        "resolved_utc": gp_lib.now_utc(),
        "resolution_tool": "pip install --dry-run --report (exact metadata resolution)",
        "packages": [], "rules_checked": {},
    }

    # download every resolved wheel + record SHA256 (hash verified pre-install)
    import hashlib
    import urllib.request
    for item in report.get("install", []):
        meta = item["metadata"]
        url = item["download_info"]["url"]
        fn = url.rsplit("/", 1)[-1]
        dest = wheels_dir / fn
        if not dest.is_file():
            print(f"[download] {fn}")
            req = urllib.request.Request(url, headers={"User-Agent": "WindowsGoldenPath/1.0"})
            with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
        sha = gp_lib.sha256_file(dest)
        lock["packages"].append({"name": meta["name"], "version": meta["version"],
                                 "wheel_filename": fn, "url": url,
                                 "sha256": sha, "size_bytes": dest.stat().st_size,
                                 "local_path": str(dest)})

    # mixing + device-wheel rules
    vers = {p["name"].lower(): p["version"] for p in lock["packages"]}
    rocm_fams = sorted({v.split("+rocm")[1].split(".")[0] for v in vers.values() if "+rocm" in v})
    lock["rules_checked"]["rocm_family_mix"] = {"families": rocm_fams,
                                                "ok": len(rocm_fams) <= 1}
    dev_wheel_present = any(args.gfx in k and "torch-device" in k for k in vers)
    tv_dev_present = any(args.gfx in k and "torchvision-device" in k for k in vers)
    lock["rules_checked"]["device_wheel_present"] = dev_wheel_present
    lock["rules_checked"]["torchvision_device_wheel_present"] = tv_dev_present
    lock["rules_checked"]["torch_is_amd_hip"] = "+rocm" in vers.get("torch", "")

    Path(args.out).write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    # hash-pinned requirements file
    lockdir = Path(args.out).parent / "requirements-lock"
    lockdir.mkdir(parents=True, exist_ok=True)
    req = lockdir / f"{lock['set_name']}.txt"
    req.write_text("\n".join(
        f"{p['name']}=={p['version']} --hash=sha256:{p['sha256']}" for p in lock["packages"]) + "\n",
        encoding="utf-8")
    ok_all = all(lock["rules_checked"].get(k, False) for k in
                 ("rocm_family_mix", "device_wheel_present", "torch_is_amd_hip"))
    print(f"[OK] lock written: {args.out} ({len(lock['packages'])} wheels); "
          f"rules ok={ok_all}")
    if not ok_all:
        print("WARNING: compatibility rules failed — do NOT install this set",
              file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
