# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Run the existing audited official-wheel discovery/resolution for gfx1201.

The historical R22A.5A discover/resolve tools list gfx1100/gfx1151 only.
This isolated adapter temporarily extends their *in-process* discovery list;
it does not change frozen integration tools or fabricate any package URL.
Usage:
  python scripts/r22a7_gfx1201/package_tools.py discover --out-dir DIR --channels nightly
  python scripts/r22a7_gfx1201/package_tools.py resolve --discovery D --out L
      --python PYTHON --channel nightly --torch-version EXACT_VERSION
      --wheels-dir DIR --include-ultralytics VERSION [--pin NAME==VERSION ...]
"""
from __future__ import annotations
import argparse
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"windows-golden-path"/"scripts"
sys.path.insert(0,str(BASE))
import gp_lib  # noqa: E402

TARGET_PACKAGES=(
    "rocm-sdk-device-gfx1201",
    "amd-torch-device-gfx1201",
    "amd-torchvision-device-gfx1201",
)
def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("discover","resolve"))
    p.add_argument("remaining",nargs=argparse.REMAINDER)
    args=p.parse_args()
    if any(x=="--gfx" or x.startswith("--gfx=") for x in args.remaining):
        p.error("gfx fixed to gfx1201: do not supply --gfx")
    if args.action=="resolve" and not any(x=="--torch-version" or x.startswith("--torch-version=") for x in args.remaining):
        p.error("exact --torch-version pin required, never select moving newest Nightly")
    old=tuple(gp_lib.DISCOVERY_PACKAGES)
    gp_lib.DISCOVERY_PACKAGES=list(dict.fromkeys((*old,*TARGET_PACKAGES)))
    target=BASE/("discover_official_wheels.py" if args.action=="discover" else "resolve_package_set.py")
    sys.argv=[str(target),*args.remaining,"--gfx","gfx1201"]
    runpy.run_path(str(target),run_name="__main__")

if __name__=="__main__":
    main()
