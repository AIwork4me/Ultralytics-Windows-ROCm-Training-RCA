# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A Phase B — MIOpen binary-provenance audit (bounded, no install).

Closes the reproducibility gap left by the R22 missions: the frozen channel
audits (evidence/raw/r22-dev, r22a-gfx1151) were assembled ad hoc; this
script is the auditable implementation of the same method:

  1. bounded download from an OFFICIAL AMD channel host only (TLS, host
     allowlist, size cap, single attempt + one bounded retry, cache dir so
     the same artifact is never re-downloaded for metadata refreshes);
  2. safe ZIP inspection via r22a5a_lib.safe_inspect_wheel (no extraction,
     no installation, no execution; path-traversal detection);
  3. wheel SHA256 + embedded MIOpen.dll SHA256 + fix-marker count +
     build-commit identity from embedded version strings;
  4. LIVE source ancestry via GitHub compare API
     f0a5d266...<build_commit> (behind_by==0 == fix is an ancestor) —
     never date inference;
  5. output in the SAME schema as the frozen r22_channel_binary_audit.json
     so verify_provenance.py --ancestry-evidence consumes it unchanged.

    python scripts/r22a5a/audit_wheel_provenance.py \
        --channel nightly --candidates release-provenance/r22a5a/latest_official_windows_candidates.json \
        --package rocm-sdk-libraries --cache-dir <dir> --out <audit.json>

Exit 0 = audit completed (verdict may be PRE_FIX — that is a RESULT, not a
failure). Exit 3 = refused (non-official host / oversize / no candidate).
"""
from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import r22a5a_lib as lib  # noqa: E402
import gp_lib  # noqa: E402

MAX_DOWNLOAD_BYTES = 3 * 1024 * 1024 * 1024  # hard bound (torch ~2.3 GiB)
DOWNLOAD_TIMEOUT_S = 900
GH_TIMEOUT_S = 45


def official_wheel_url(channel: str, url: str) -> bool:
    host = lib.url_host(url or "")
    ok = host in lib.allowed_download_hosts() and gp_lib.url_channel(url) == channel
    return ok


def bounded_download(url: str, dest: Path) -> tuple[Path | None, str | None]:
    """Single-attempt bounded download (TLS default context, host allowlist
    enforced by caller). Refuses to start when Content-Length exceeds the
    bound; refuses to keep partial oversize files."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={
        "User-Agent": "R22A5A-ProvenanceAudit/1.0 (+https://github.com/AIwork4me)"})
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_S, context=ctx) as r:
            length = int(r.headers.get("Content-Length") or 0)
            if length and length > MAX_DOWNLOAD_BYTES:
                return None, f"Content-Length {length} exceeds bound {MAX_DOWNLOAD_BYTES}"
            total = 0
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        f.close()
                        tmp.unlink(missing_ok=True)
                        return None, f"stream exceeded bound {MAX_DOWNLOAD_BYTES}"
                    f.write(chunk)
        tmp.replace(dest)
        return dest, None
    except Exception as e:  # noqa: BLE001 — recorded honestly
        return None, f"{type(e).__name__}: {e}"


def gh_compare(build_commit: str) -> dict:
    """Live ancestry f0a5d266...<commit> via gh api (bounded, honest errors)."""
    cmd = ["gh", "api", f"repos/ROCm/rocm-libraries/compare/"
           f"{lib.MERGED_FIX_COMMIT}...{build_commit}"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=GH_TIMEOUT_S,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return {"error": f"gh exit {r.returncode}: {r.stderr.strip()[-200:]}"}
        d = json.loads(r.stdout)
        return {"status": d.get("status"), "ahead_by": d.get("ahead_by"),
                "behind_by": d.get("behind_by"),
                "commit_date_gh": (d.get("merge_base_commit") or {}).get("commit",
                                                                        {}).get("committer", {}).get("date")}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def pick_candidate(candidates_path: Path, channel: str, package: str) -> dict | None:
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    rows = [c for c in data["candidates"]
            if c.get("channel") == channel and c.get("package") == package
            and c.get("wheel_url")]
    if not rows:
        return None
    return max(rows, key=lambda c: (lib.version_sort_key(c["version"]),
                                    c.get("wheel_filename") or ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=None, help="explicit wheel URL (official host only)")
    ap.add_argument("--channel", required=True, choices=list(gp_lib.OFFICIAL_CHANNELS))
    ap.add_argument("--candidates", default=None,
                    help="latest_official_windows_candidates.json (pick newest wheel)")
    ap.add_argument("--package", default="rocm-sdk-libraries")
    ap.add_argument("--cache-dir", required=True,
                    help="download cache (artifact fetched once, reused)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--skip-download", action="store_true",
                    help="audit an already-cached file only (offline re-verify)")
    args = ap.parse_args()

    url = args.url
    if not url:
        if not args.candidates:
            print("REFUSED: need --url or --candidates", file=sys.stderr)
            sys.exit(3)
        cand = pick_candidate(Path(args.candidates), args.channel, args.package)
        if cand is None:
            print(f"REFUSED: no {args.package} wheel found on {args.channel} "
                  "in candidates file", file=sys.stderr)
            sys.exit(3)
        url = cand["wheel_url"]
    if not official_wheel_url(args.channel, url):
        print(f"REFUSED: {url!r} is not on the exact official {args.channel} "
              "channel host (allowlist)", file=sys.stderr)
        sys.exit(3)

    from urllib.parse import unquote
    fn = unquote(url.rsplit("/", 1)[-1])
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / fn
    download_note = None
    if dest.is_file():
        download_note = "cache hit — artifact already fetched (never re-downloaded)"
    elif args.skip_download:
        print(f"REFUSED: --skip-download but {dest} not cached", file=sys.stderr)
        sys.exit(3)
    else:
        print(f"[download] {url} -> {dest}", flush=True)
        got, err = bounded_download(url, dest)
        if got is None:
            print(f"REFUSED: download failed: {err}", file=sys.stderr)
            sys.exit(3)
        download_note = "downloaded this run (bounded, single artifact)"

    insp = lib.safe_inspect_wheel(dest, expect_name=args.package)
    if not insp["ok"]:
        print(f"REFUSED: wheel inspection failed: {insp['errors']}", file=sys.stderr)
        sys.exit(3)
    dll = insp.get("miopen_dll") or {}
    build_commit = dll.get("build_commit")
    ancestry = gh_compare(build_commit) if build_commit else {"error": "no build identity"}

    fix_present = None
    if not ancestry.get("error"):
        fix_present = bool(ancestry.get("status") in ("ahead", "diverged")
                           and ancestry.get("behind_by") == 0)
    audit_entry = {
        "channel": args.channel,
        "package": args.package,
        "wheel": insp["metadata"].get("name"),
        "wheel_version": insp["metadata"].get("version"),
        "wheel_filename": fn,
        "wheel_url": url,
        "wheel_sha256": insp["wheel_sha256"],
        "wheel_bytes": insp["size_bytes"],
        "wheel_requires_python": insp["metadata"].get("requires_python"),
        "wheel_requires_dist": insp["metadata"].get("requires_dist"),
        "download": download_note,
        "miopen_dll": {
            "member": dll.get("member"),
            "sha256": dll.get("sha256"),
            "bytes": dll.get("bytes"),
            "version_strings": dll.get("version_strings"),
            "build_commit": build_commit,
            "marker_miopen_initializer_list": dll.get(
                "marker_miopen_initializer_list"),
        },
        "ancestry": {
            "compare": f"{lib.MERGED_FIX_COMMIT[:9]}...{build_commit}",
            **ancestry,
        },
        "fix_present": fix_present,
        "verdict": ("POST_FIX_LIBRARIES" if fix_present else
                    "PRE_FIX" if fix_present is False else
                    "BINARY_PROVENANCE_INCONCLUSIVE"),
        "caveat": "marker is a screening signal; the ancestry compare above is "
                  "the source-lineage proof; a positive verdict still requires "
                  "the R22A.5B no-STL runtime gate",
    }
    record = {
        "run_id": args.run_id or f"R22A5A-WHEEL-AUDIT-{lib.now_utc()[:10]}",
        "mission": "R22A.5A",
        "timestamp": lib.now_utc(),
        "method": "bounded official-channel download; ZIP-inspected without "
                  "installation/extraction; SHA256 wheel+DLL; marker count; "
                  "GitHub compare API ancestry vs merged fix (never date inference)",
        "merged_fix_commit": lib.MERGED_FIX_COMMIT,
        "audits": [audit_entry],
    }
    out = lib.dump_json(record, Path(args.out))
    print(f"[OK] {out}")
    print(json.dumps({k: audit_entry[k] for k in
                      ("channel", "wheel_version", "wheel_sha256", "fix_present",
                       "verdict")}, indent=1))
    print(json.dumps(audit_entry["miopen_dll"], indent=1))
    print(json.dumps(audit_entry["ancestry"], indent=1))


if __name__ == "__main__":
    main()
