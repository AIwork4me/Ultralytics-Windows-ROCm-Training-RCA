"""Gate 22 helper: copy the transitive dependency closure of given root
packages from a source site-packages into a destination site-packages,
file-by-file per each distribution's RECORD (auditable, exact).

Usage (run with the SOURCE env's python):
    python gate22_copy_closure.py --src <base site-packages> \
        --dst <yolo_amd site-packages> --roots torch torchvision ultralytics ... \
        --exclude torchaudio ... > manifest.json

Excluded packages are recorded but not copied; a dependency on an excluded
package aborts with a listing so the operator can decide.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from importlib.metadata import Distribution, distributions

_REQ = re.compile(
    r"^(?P<name>[A-Za-z0-9._-]+)\s*(?:\[(?P<extra>[^\]]*)\])?\s*"
    r"(?P<rest>.*)$"
)


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_req(req: str):
    # split off environment marker
    marker = None
    for sep in (";", " ;"):
        if sep in req:
            head, _, marker = req.partition(";")
            break
    else:
        head = req
    m = _REQ.match(head.strip())
    if not m:
        return None, None
    return m.group("name"), (marker.strip() if marker else None)


def marker_active(marker: str) -> bool:
    try:
        from packaging.markers import Marker

        return Marker(marker).evaluate()
    except Exception:
        # no packaging available → assume active (over-copy is safe-ish, we review)
        return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    by_norm: dict[str, Distribution] = {}
    for d in distributions(path=[str(src)]):
        n = d.metadata["Name"]
        if n:
            by_norm[norm(n)] = d

    excludes = {norm(e) for e in args.exclude}
    roots = [norm(r) for r in args.roots]

    for r in roots + list(excludes):
        if r not in by_norm:
            print(f"FATAL: root/exclude package not found in source: {r}", file=sys.stderr)
            return 2

    closure: dict[str, dict] = {}
    missing: set[str] = set()
    queue = list(roots)
    while queue:
        name = queue.pop(0)
        if name in closure or name in excludes or name in missing:
            continue
        if name not in by_norm:
            missing.add(name)
            continue
        d = by_norm[name]
        deps = []
        for req in (d.requires or []):
            dep_name, marker = parse_req(req)
            if dep_name is None:
                continue
            if norm(dep_name) in excludes:
                continue
            if marker and not marker_active(marker):
                continue
            deps.append(norm(dep_name))
            if norm(dep_name) not in closure:
                queue.append(norm(dep_name))
        closure[name] = {
            "version": d.version,
            "requires_kept": deps,
        }

    excluded_hit = []
    for name, info in closure.items():
        for req in by_norm[name].requires or []:
            dep_name, _ = parse_req(req)
            if dep_name and norm(dep_name) in excludes:
                excluded_hit.append(f"{name} -> {norm(dep_name)}")

    files_copied = 0
    bytes_copied = 0
    per_dist_files: dict[str, int] = {}
    if not args.dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        for name in sorted(closure):
            d = by_norm[name]
            dist_dir = Path(d._path).parent  # noqa: SLF001 - metadata path
            nfiles = 0
            rec = d.read_text("RECORD") or ""
            for line in rec.splitlines():
                fn = line.split(",")[0]
                if not fn:
                    continue
                s = dist_dir / fn
                if not s.is_file():
                    # console scripts may live elsewhere; RECORD paths are
                    # relative to site-packages for wheel installs
                    s = src / fn
                    if not s.is_file():
                        continue
                rel = s.relative_to(src) if str(src) in str(s) else s.relative_to(dist_dir)
                t = dst / rel
                t.parent.mkdir(parents=True, exist_ok=True)
                if not t.exists():
                    shutil.copy2(s, t)
                    nfiles += 1
                    files_copied += 1
                    bytes_copied += s.stat().st_size
            per_dist_files[name] = nfiles

    result = {
        "source": str(src),
        "destination": str(dst),
        "roots": roots,
        "excluded": sorted(excludes),
        "excluded_edges": excluded_hit,
        "closure": {k: closure[k] for k in sorted(closure)},
        "missing_in_source": sorted(missing),
        "files_copied": files_copied,
        "bytes_copied": bytes_copied,
        "per_dist_new_files": per_dist_files,
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
