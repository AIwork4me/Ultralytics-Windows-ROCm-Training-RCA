"""Gate L09: discover the ROCm wheel layout inside the uv venv — no /opt/rocm assumptions.

Locates installed distributions (rocm, _rocm_sdk_core, _rocm_sdk_libraries,
_rocm_sdk_devel if present, HIP) and the important directories for:
compilers (amdclang++/clang++/hipcc), hiprtc, MIOpen, rocBLAS, hipamd runtime,
CMake package config roots, include roots, lib roots, bin roots.

Output: machine-readable JSON on stdout.
"""

from __future__ import annotations

import importlib.metadata as im
import json
import os
import site
import sys
from pathlib import Path

KEY_DISTS = [
    "rocm",
    "rocm-sdk-core",
    "rocm-sdk-devel",
    "rocm-sdk-libraries",
    "rocm-sdk-device-gfx1151",
    "torch",
]

# interesting relative targets inside a dist root
PROBES = {
    "bin": "bin",
    "lib": "lib",
    "lib64": "lib64",
    "include": "include",
    "cmake_root": "lib/cmake",
    "llvm_bin": "llvm/bin",
    "lib_llvm": "lib/llvm",
}


def dist_site_packages(dist_name: str) -> list[Path]:
    """Return site-package dirs containing the named distribution."""
    roots = []
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        p = Path(sp)
        if (p / f"{dist_name.replace('-', '_')}.dist-info").exists() or (
            p / f"{dist_name}.dist-info"
        ).exists():
            roots.append(p)
    return roots


def find_dist_dirs() -> dict[str, list[str]]:
    """Map dist name -> package dirs, via each dist-info dir's parent."""
    out: dict[str, list[str]] = {}
    for d in im.distributions():
        name = (d.metadata["Name"] or "").lower()
        if name in KEY_DISTS or name.startswith(("_rocm_sdk", "rocm")):
            sp_root = Path(d._path).parent  # site-packages dir holding dist-info
            pkgdir = sp_root / name.replace("-", "_")
            if not pkgdir.is_dir():
                pkgdir = sp_root / name
            out.setdefault(name, [])
            if pkgdir.is_dir() and str(pkgdir) not in out[name]:
                out[name].append(str(pkgdir))
    return out


def file_probe(root: Path) -> dict:
    found = {}
    for label, rel in PROBES.items():
        p = root / rel
        if p.is_dir():
            found[label] = str(p)
    # key executables / libraries anywhere shallow
    for name in ("amdclang++", "amdclang", "clang++", "clang", "hipcc", "rocminfo", "cmake", "ninja"):
        hits = []
        for sub in ("bin", "llvm/bin", "llvm/lib/llvm/bin"):
            cand = root / sub / name
            if cand.exists():
                hits.append(str(cand))
        if hits:
            found[f"exe_{name}"] = hits
    for pat in ("libMIOpen.so*", "libhiprtc.so*", "libamdhip64.so*", "libamd_comgr.so*",
                "librocblas.so*", "libhiprtc-builtins.so*"):
        hits = []
        for sub in ("lib", "lib64"):
            d = root / sub
            if d.is_dir():
                hits.extend(str(x) for x in sorted(d.glob(pat)))
        if hits:
            found[f"lib_{pat.rstrip('*')}"] = hits[:8]
    return found


def main() -> int:
    result = {
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "python_executable": sys.executable,
        "sys_prefix": sys.prefix,
        "site_packages": site.getsitepackages(),
        "dist_dirs": find_dist_dirs(),
        "dist_details": {},
        "tool_search": {},
    }

    for name, roots in result["dist_dirs"].items():
        det = {}
        for r in roots:
            rp = Path(r)
            det[r] = {
                "exists": rp.is_dir(),
                "probes": file_probe(rp),
            }
        result["dist_details"][name] = det

    # cross-tree tool search across all site-packages roots
    all_bins: set[Path] = set()
    for sp in site.getsitepackages():
        sp = Path(sp)
        for pkg in sp.iterdir():
            if pkg.is_dir() and (pkg.name.startswith("_rocm_sdk") or pkg.name in ("rocm", "HIP")):
                for sub in (pkg / "bin", pkg / "llvm" / "bin"):
                    if sub.is_dir():
                        all_bins.add(sub)
                # devel-style layouts
                for sub in pkg.glob("*/bin"):
                    if sub.is_dir():
                        all_bins.add(sub)
    tools = {}
    for tool in ("amdclang++", "amdclang", "clang++", "clang", "hipcc", "hiprtc", "rocminfo", "cmake", "ninja"):
        hits = []
        for b in all_bins:
            cand = b / tool
            if cand.exists():
                hits.append(str(cand))
            else:
                hits.extend(str(x) for x in sorted(b.glob(tool + "*"))[:6])
        if hits:
            tools[tool] = sorted(set(hits))[:12]
    result["tool_search"] = tools

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
