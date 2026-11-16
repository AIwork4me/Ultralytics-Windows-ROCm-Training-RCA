"""Verification contract v2 — audits the release-closure evidence WITHOUT a GPU.

    python scripts/verify_release_closure.py [--root <repo-root>] [--json-only]

v2 upgrades (mission §3.4 + P9.4 — structural checks alone were insufficient):
  - validates ACTUAL ASSERTIONS, not just status vocabulary: recomputes
    t07/t08/t16 verdicts from embedded per-step evidence and FAILs a record
    whose claimed status contradicts its own data
  - SKIP is never counted as functional PASS anywhere
  - every PASS-claiming GPU JSON carries binary (loaded-DLL SHA256) + GPU
    (HIP+device) provenance; loaded-DLL SHA must be CONSISTENT within one
    environment_id (catches env contamination)
  - run_id consistency: result JSON run_id must appear in its stage/probe
    logs; environment_id must agree between JSON and log headers
  - expected test cases present per lifecycle (t01,t03..t15; +t16 for AMP)
  - G4 records must reconcile configured vs observed epochs and preserve
    results.csv + in-process DLL probe
  - every strong claim in CLAIMS_AND_EVIDENCE.md cites at least one
    existing evidence file
  - adversarial self-test: scripts/test_verify_release_closure.py builds
    known-bad synthetic records and proves this verifier REJECTS each one

Legacy tolerance (disclosed in P8_INDEPENDENT_AUDIT.md): pre-P9 records
without run_id/DLL probes only require HIP+torch provenance. New (P9-era)
records are held to the full contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ALLOWED = {"PASS", "FAIL", "EXPECTED_FAIL", "SKIP", "BLOCKED", "NOT_RUN", "INCONCLUSIVE"}
OFFICIAL_PATTERNS = [
    r"officially supported by AMD", r"officially supported by Ultralytics",
    r"supported on all Windows", r"works on all GPUs",
]
REQUIRED = {
    "release-provenance": ["G0_VERDICT.md", "RELEASE_LINEAGE.md", "RELEASE_MATRIX.csv",
                           "WHEEL_MANIFEST.json", "BINARY_PROVENANCE.json", "LOADED_DLL_REPORT.json"],
    "windows-training-validation": ["G1_VERDICT.md", "G2_VERDICT.md"],
    "amp-rca": ["ROOT_CAUSE.md", "MINIMAL_REPRO.py", "PRECISION_COMPARISON.csv", "G3_VERDICT.md"],
    "upstream-readiness": ["AMP_FIX_PR_DRAFT.md", "TEST_PR_DRAFT.md", "DOCS_PR_DRAFT.md",
                           "MAINTAINER_CHECKLIST.md"],
    "platform-matrix": ["GPU_SUPPORT_MATRIX.md", "WINDOWS_GFX1151.md"],
}
LIFECYCLE_EXPECTED = {"t01_gpu_pretrained_inference", "t03_gpu_training_init", "t04_one_epoch_smoke",
                      "t05_multi_epoch_interrupted", "t06_loss_finite_throughout",
                      "t07_backward_gradient_finite", "t08_optimizer_step",
                      "t09_save_last_pt", "t10_save_best_pt", "t11_reload_checkpoint",
                      "t12_resume_interrupted", "t13_gpu_val_saved_model",
                      "t14_gpu_predict_saved_model", "t15_metrics_before_after_reload"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- R22A.2.1 P0-B: evidence integrity against the EXACT GIT TREE -----------

def git_tree_sha256(root: Path) -> dict[str, str] | None:
    """path -> SHA256 of blob content AT HEAD (the committed tree, not the
    working directory — a checksum matching a local but uncommitted file is
    NOT sufficient). Returns None when git/HEAD is unavailable (callers
    fail-closed on that)."""
    import subprocess as _sp
    try:
        names = _sp.run(["git", "ls-tree", "-r", "--name-only", "HEAD"],
                        capture_output=True, text=True, cwd=root, timeout=120)
        if names.returncode != 0:
            return None
        paths = [p for p in names.stdout.splitlines() if p.strip()]
        batch = _sp.Popen(["git", "cat-file", "--batch"], stdin=_sp.PIPE,
                          stdout=_sp.PIPE, cwd=root)
        out: dict[str, str] = {}
        for path in paths:
            batch.stdin.write(f"HEAD:{path}".encode("utf-8") + b"\n")
            batch.stdin.flush()
            header = batch.stdout.readline().decode("utf-8", "replace").strip()
            if not header or header.endswith(" missing"):
                out[path] = None  # type: ignore[assignment]
                continue
            _sha, _kind, size = header.split(" ", 2)
            body = batch.stdout.read(int(size))
            batch.stdout.read(1)  # trailing newline
            out[path] = hashlib.sha256(body).hexdigest()
        batch.stdin.close()
        batch.wait(timeout=60)
        return out
    except (OSError, ValueError, _sp.TimeoutExpired):
        return None


def audit_git_tree_evidence(root: Path, audit) -> dict | None:
    """P0-B contract: every manifest entry and every SHA256SUMS entry must
    resolve to a COMMITTED file whose content matches its declared hash.
    Missing files, hash mismatches, and worktree-only (uncommitted) files are
    violations; historical manifests are read, never rewritten."""
    tree = git_tree_sha256(root)
    if tree is None:
        audit.check("git-tree:available", False,
                    "git tree unavailable — evidence cannot be verified against "
                    "the exact Git tree (fail-closed)")
        return None
    audit.check("git-tree:available", True, f"{len(tree)} tracked paths at HEAD")

    manifest_path = root / "evidence" / "manifest.json"
    entries: list = []
    if manifest_path.is_file():
        try:
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            audit.check("git-tree:manifest-readable", False, "manifest.json unreadable")
        for e in entries:
            p = str(e.get("path") or "")
            declared = str(e.get("sha256") or "")
            actual = tree.get(p)
            if actual is None:
                audit.check(f"git-tree:manifest:{p}", False,
                            "manifest entry resolves to no committed file "
                            "(uncommitted or missing)")
            elif actual != declared:
                audit.check(f"git-tree:manifest:{p}", False,
                            f"committed content hash {actual[:12]}… != manifest "
                            f"{declared[:12]}…")

    # converse completeness for the CURRENT-era packs (r22a2*): every committed
    # evidence file must carry a manifest entry. Historical phase packs are
    # untouched by this rule (their manifests predate the contract).
    manifest_paths = {str(e.get("path") or "") for e in entries}
    for pack in sorted((root / "evidence" / "raw").glob("r22a2*")):
        if not pack.is_dir():
            continue
        for f in sorted(pack.rglob("*")):
            if f.is_file():
                rel = f.relative_to(root).as_posix()
                audit.check(f"git-tree:pack-complete:{rel}", rel in manifest_paths,
                            "committed r22a2* evidence file with no manifest entry")

    sums_files = [root / "evidence" / "SHA256SUMS.txt"]
    sums_files += sorted((root / "evidence" / "raw").glob("*/SHA256SUMS.txt"))
    sums_files += sorted((root / "windows-golden-path" / "reports").glob("*/SHA256SUMS.txt"))
    for sf in sums_files:
        if not sf.is_file():
            continue
        base = sf.parent
        for ln in sf.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.rstrip("\r\n")
            if not ln.strip() or ln.startswith("#"):
                continue
            parts = ln.split(None, 1)
            if len(parts) != 2:
                audit.check(f"git-tree:sums-parse:{sf.name}", False,
                            f"unparseable line {ln[:60]!r}")
                continue
            declared, rel = parts[0], parts[1].strip().lstrip("*").replace("\\", "/")
            rel = rel if rel.count("/") >= 2 else f"{base.relative_to(root).as_posix()}/{rel}"
            actual = tree.get(rel)
            if actual is None:
                audit.check(f"git-tree:sums:{rel}", False,
                            f"{sf.name} entry resolves to no committed file "
                            "(uncommitted or missing)")
            elif actual != declared:
                audit.check(f"git-tree:sums:{rel}", False,
                            f"committed content hash {actual[:12]}… != declared "
                            f"{declared[:12]}… ({sf.name})")
    return tree


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.ok = True

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            self.ok = False

    @property
    def violations(self) -> list[str]:
        return [f"{c['check']}: {c['detail']}" for c in self.checks if not c["ok"]]


def recompute_t07(rec: dict) -> str:
    """Authoritative t07 status from embedded step evidence (strict — no
    unconditional AMP gradient PASS)."""
    fails = rec.get("failed_step_indices") or []
    n = rec.get("n_steps", 0)
    if fails:
        return "FAIL"
    if n == 0:
        return "SKIP"
    return "PASS"


def recompute_t08(rec: dict, detail: dict | None) -> str:
    counts = (detail or {}).get("counts") or rec.get("counts") or {}
    if counts.get("STUCK_FAILURE", 0) or counts.get("BAD_GRAD_UPDATE", 0):
        return "FAIL"
    if counts.get("UPDATED", 0) >= 1:
        return "PASS"
    return "SKIP"


def recompute_t16(rec: dict, steps_full: list | None = None) -> str:
    """t16 verdict recomputation. The harness classifies fallback (no AMP step
    ever active) as SKIP regardless of update counts — an FP32 run with 887
    updates proves nothing about AMP (mission §4.4)."""
    counts = rec.get("counts") or {}
    if counts.get("STUCK_FAILURE", 0) or counts.get("BAD_GRAD_UPDATE", 0):
        return "FAIL"
    if steps_full is not None and not any(s.get("amp_active") for s in steps_full):
        return "SKIP"  # check_amp fallback: no AMP semantics exercised
    if counts.get("UPDATED", 0) >= (rec.get("min_updated_required") or 1):
        return "PASS"
    return "SKIP"


def audit_g2_json(jf: Path, d: dict, audit: Audit, dll_by_env: dict, devices: set) -> None:
    name = jf.name
    tests = d.get("tests") or {}
    statuses = [t.get("status") for t in tests.values()]
    for t in tests.values():
        audit.check(f"status-vocab:{name}", t.get("status") in ALLOWED,
                    f"bad status {t.get('status')!r}")
    new_format = "run_id" in d
    all_pass_like = bool(tests) and all(s in ("PASS", "SKIP") for s in statuses)
    n_pass = sum(1 for s in statuses if s == "PASS")

    # expected test cases present (t02 intentionally absent in 8.4.182 harness)
    if new_format and (d.get("args") or {}).get("stage", "resume") != "main":
        missing = LIFECYCLE_EXPECTED - set(tests)
        audit.check(f"expected-tests:{name}", not missing,
                    f"missing lifecycle tests: {sorted(missing)}" if missing else "ok")
        if (d.get("args") or {}).get("amp") == "True":
            audit.check(f"expected-tests-t16:{name}", "t16_amp_repeated_updates" in tests,
                        "AMP lifecycle without t16 repeated-updates record")
    # SKIP is never functional PASS
    if all_pass_like and n_pass == 0:
        audit.check(f"skip-not-pass:{name}", False,
                    "all tests SKIP but record would be treated as success — SKIP≠PASS")

    # provenance: every PASS claim needs binary + GPU provenance
    dll = d.get("loaded_dll") or {}
    env = d.get("environment") or {}
    if env.get("device"):
        devices.add(env["device"])
    has_gpu_prov = bool(env.get("hip")) and bool(env.get("gpu_authentic", True)) and bool(env.get("device"))
    has_bin_prov = bool(dll.get("sha256"))
    if not has_bin_prov:
        # historical convention (P8 audit): probe ran post-hoc as a sibling
        # *_loaddll.json in the same run dir — accepted with an explicit note
        sibling = jf.parent / f"{jf.stem}_loaddll.json"
        if sibling.is_file():
            try:
                ld = json.loads(sibling.read_text(encoding="utf-8"))
                has_bin_prov = bool((ld.get("miopen_loaded") or {}).get("sha256"))
                if has_bin_prov:
                    audit.check(f"dll-provenance:{name}", True,
                                "provenance via post-hoc sibling probe (disclosed P8 convention)")
            except json.JSONDecodeError:
                pass
    if n_pass > 0:
        audit.check(f"gpu-provenance:{name}", has_gpu_prov, "PASS record without HIP/device provenance")
        audit.check(f"dll-provenance:{name}", has_bin_prov,
                    "PASS record without in-process loaded-DLL SHA256")
    else:
        audit.check(f"gpu-provenance:{name}", bool(env.get("hip")) or not env,
                    "record without HIP provenance (no PASS claimed)")

    # new-format strictness: run_id in logs, env_id consistency, DLL per env
    rid = d.get("run_id")
    env_id = d.get("environment_id")
    if new_format:
        logs = [jf.parent / f"{jf.stem}_{stage}.log" for stage in ("main", "resume")]
        for lg in logs:
            if not lg.is_file() or not lg.read_text(encoding="utf-8", errors="replace").strip():
                audit.check(f"raw-log:{name}", False, f"missing/empty stage log {lg.name}")
            elif rid and rid not in lg.read_text(encoding="utf-8", errors="replace"):
                audit.check(f"run-id-consistency:{name}", False,
                            f"run_id {rid} absent from {lg.name}")
        env_log = jf.parent / f"{jf.stem}_probe.log"
        if env_log.is_file() and env_id and env_id not in env_log.read_text(encoding="utf-8", errors="replace"):
            audit.check(f"env-id-consistency:{name}", False,
                        f"environment_id {env_id} absent from {env_log.name}")
        # loaddll probe cross-check
        loaddll = jf.parent / f"{jf.stem}_loaddll.json"
        if loaddll.is_file():
            try:
                ld = json.loads(loaddll.read_text(encoding="utf-8"))
                m_sha = (ld.get("miopen_loaded") or {}).get("sha256")
                audit.check(f"dll-crosscheck:{name}",
                            (not has_bin_prov) or m_sha == dll.get("sha256"),
                            f"loaded_dll.sha256 {dll.get('sha256','')[:8]} != probe {str(m_sha)[:8]}")
            except json.JSONDecodeError:
                audit.check(f"dll-crosscheck:{name}", False, "unreadable loaddll JSON")
        # per-environment DLL consistency (contamination detector)
        if has_bin_prov and env_id:
            prev = dll_by_env.setdefault(env_id, dll["sha256"])
            audit.check(f"dll-env-consistency[{env_id}]:{name}", prev == dll["sha256"],
                        f"environment {env_id} shows DIFFERENT loaded MIOpen SHAs: "
                        f"{prev[:12]} vs {dll['sha256'][:12]} — env contamination")

    # assertion recomputation — ONLY for P9-era records carrying embedded step
    # audit data (legacy records were audited under the legacy contract and
    # keep their historical statuses; reinterpreting them via missing new
    # fields would fabricate violations, not find them)
    sad = d.get("step_audit_detail") or {}
    for tname, fn in (("t07_backward_gradient_finite", recompute_t07),
                      ("t08_optimizer_step", recompute_t08),
                      ("t16_amp_repeated_updates", recompute_t16)):
        if tname in tests and not sad and tname != "t16_amp_repeated_updates":
            audit.check(f"assertion-skip-legacy:{name}", True,
                        "legacy record (no step_audit_detail) — status kept, not recomputed")
            continue
        if tname in tests and tname in ("t07_backward_gradient_finite", "t08_optimizer_step"):
            claimed = tests[tname].get("status")
            detail = sad.get("main") if tname == "t07_backward_gradient_finite" else None
            if tname == "t08_optimizer_step":
                merged_counts = {}
                for lbl, s in sad.items():
                    for k, v in (s.get("counts") or {}).items():
                        merged_counts[k] = merged_counts.get(k, 0) + v
                actual = fn(tests[tname], {"counts": merged_counts})
            else:
                actual = fn(tests[tname])
            audit.check(f"assertion:{name}:{tname}", claimed == actual,
                        f"claimed {claimed} but embedded evidence recomputes to {actual}")
        if tname == "t16_amp_repeated_updates" and tname in tests:
            claimed = tests[tname].get("status")
            ssr = d.get("_stage_step_records") or {}
            amp = (ssr.get("ampupd") or (sad.get("ampupd") if isinstance(sad.get("ampupd"), dict) else {}))
            steps_full = (amp or {}).get("steps_full")
            actual = fn(tests[tname], steps_full)
            audit.check(f"assertion:{name}:{tname}", claimed == actual,
                        f"claimed {claimed} but embedded counts recompute to {actual}")


def audit_g4_json(jf: Path, d: dict, audit: Audit, devices: set) -> None:
    name = jf.name
    env = d.get("environment") or {}
    if env.get("device"):
        devices.add(env["device"])
    if "run_id" in d:  # P9-era record: full contract
        recon = d.get("epoch_reconciliation") or {}
        runs = d.get("runs") or {}
        if recon:
            audit.check(f"epoch-reconciled:{name}", recon.get("reconciled") is True,
                        f"epoch accounting not reconciled: {recon}")
        else:
            ok = all((r.get("epochs_reconciled") is True) for r in runs.values()) and runs
            audit.check(f"epoch-reconciled:{name}", ok, "perf record without per-run epoch reconciliation")
        audit.check(f"csv-preserved:{name}",
                    (bool(d.get("results_csv_text")) if not runs
                     else all(bool(r.get("results_csv_text")) for r in runs.values())),
                    "per-epoch results.csv not preserved (audit B-F9 regression)")
        probes = ([d.get("dll_provenance")] if d.get("dll_provenance") else
                  [r.get("dll_provenance") for r in runs.values()])
        shas = {(p or {}).get("miopen_loaded", {}).get("sha256") if p else None for p in probes}
        audit.check(f"dll-probe:{name}", all(probes) and None not in shas and len(shas) == 1,
                    f"missing or inconsistent in-process DLL probes: {shas}")
        audit.check(f"wall-samples:{name}",
                    bool(d.get("wall_samples")) or all(r.get("results_csv_text") for r in runs.values()),
                    "no per-epoch wall-clock samples")
    else:
        audit.check(f"gpu-provenance:{name}", bool(env.get("hip")) and bool(env.get("torch")),
                    "G4 record without HIP/torch provenance (legacy record — disclosed deviation)")


def audit_g3_json(jf: Path, d: dict, audit: Audit, devices: set) -> None:
    name = jf.name
    env = d.get("environment") or {}
    if env.get("device"):
        devices.add(env["device"])
    if "run_id" in d:
        # record types: paired-box (repeats), learning (runs), evi-repro (probes),
        # checkamp-validation (modes — subprocess GPU checks on a PYTHONPATH-
        # injected ultralytics tree; the outer process never initializes HIP,
        # so in-process DLL provenance is not applicable by design)
        if "modes" in d and "ultralytics_imported" in d.get("summary", {}):
            vals = d["summary"].get("verdicts") or {}
            audit.check(f"checkamp-verdicts:{name}", bool(vals),
                        f"checkamp record without verdict map: {vals}")
            # a None verdict is honest ONLY when the mode carries crash evidence
            for m, r in (d.get("modes") or {}).items():
                if r.get("check_amp_verdict") is None:
                    crash = "AcceleratorError" in (r.get("stderr_tail") or "") or \
                            "invalid kernel" in (r.get("stderr_tail") or "")
                    audit.check(f"checkamp-crash-evidence:{name}:{m}", crash,
                                f"mode {m} has no verdict AND no archived crash evidence")
            audit.check(f"checkamp-version:{name}",
                        any(v == "8.4.212" for v in (d["summary"].get("ultralytics_imported") or []))
                        or any("upstream_ultralytics" in (r.get("stderr_tail") or "")
                               for r in (d.get("modes") or {}).values()),
                        f"validated tree version not traceable: {d['summary'].get('ultralytics_imported')}")
            for m, r in (d.get("modes") or {}).items():
                audit.check(f"checkamp-mode:{name}:{m}", isinstance(r.get("check_amp_verdict"), bool)
                            or r.get("exit") != 0,
                            f"mode {m} lacks a verdict and did not exit cleanly")
        elif "probes" in d:  # EvaluateInvokers repro: probes ran in subprocesses on
            # the target env; parent never inits the GPU, so the in-process probe
            # lives in a sibling *_loaddll.json (same convention as g2)
            audit.check(f"probes-present:{name}", bool(d.get("probes")),
                        "evi record without probe list")
            audit.check(f"probe-python-recorded:{name}", bool(d.get("python")),
                        "evi record without target-env python recorded")
            sibling = jf.parent / f"{jf.stem}_loaddll.json"
            has = sibling.is_file() and bool(
                ((json.loads(sibling.read_text(encoding="utf-8")).get("miopen_loaded")) or {}).get("sha256"))
            audit.check(f"dll-probe:{name}", has,
                        "evi record without sibling loaded-DLL probe")
        elif "runs" in d:  # matched FP32-vs-AMP learning: per-run probes
            runs = d["runs"]
            probes = [r.get("dll_provenance") for r in runs.values()]
            shas = {(p or {}).get("miopen_loaded", {}).get("sha256") if p else None for p in probes}
            audit.check(f"dll-probe:{name}", all(probes) and None not in shas and len(shas) == 1,
                        f"learning record missing/inconsistent per-run DLL probes: {shas}")
            for tag, r in runs.items():
                audit.check(f"learning-verdict:{name}:{tag}",
                            r.get("verdict") in ALLOWED,
                            f"bad learning verdict {r.get('verdict')!r}")
        else:  # paired-box capture
            prov = d.get("dll_provenance") or {}
            audit.check(f"dll-probe:{name}", bool((prov.get("miopen_loaded") or {}).get("sha256")),
                        "P9-era G3 record without in-process DLL probe")
            audit.check(f"negctrl:{name}",
                        d.get("summary", {}).get("negative_controls_all_caught") is True,
                        "paired-box record without all negative controls caught")
    elif "gpu_authentic" in env:
        audit.check(f"gpu-provenance:{name}", bool(env.get("hip")) and env.get("gpu_authentic"),
                    "AMP audit run without HIP provenance")
    else:
        audit.check(f"gpu-provenance:{name}", bool(env.get("hip")) and bool(env.get("torch")),
                    "AMP training record without HIP/torch provenance (legacy — disclosed)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    audit = Audit()

    # 1. required deliverables exist
    for dr, files in REQUIRED.items():
        for f in files:
            audit.check(f"exists:{dr}/{f}", (root / dr / f).is_file())

    # 2. raw evidence: lifecycle JSONs — assertions, provenance, run/env ids
    raw = root / "windows-training-validation" / "raw"
    dll_by_env: dict[str, str] = {}
    devices: set[str] = set()
    if raw.is_dir():
        for jf in sorted(raw.glob("g2_*.json")):
            if jf.name.endswith("loaddll.json"):
                try:
                    dd = json.loads(jf.read_text(encoding="utf-8"))
                    audit.check(f"gpu-provenance:{jf.name}",
                                bool((dd.get("miopen_loaded") or {}).get("sha256")),
                                "raw probe missing miopen_loaded.sha256")
                except json.JSONDecodeError:
                    audit.check(f"json:{jf.name}", False, "unreadable JSON")
                continue
            try:
                d = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                audit.check(f"json:{jf.name}", False, "unreadable JSON")
                continue
            audit_g2_json(jf, d, audit, dll_by_env, devices)
        for jf in sorted(raw.glob("g3_*.json")):
            if jf.name.endswith("_loaddll.json"):
                continue  # sibling probe output (same convention as g2)
            try:
                audit_g3_json(jf, json.loads(jf.read_text(encoding="utf-8")), audit, devices)
            except json.JSONDecodeError:
                audit.check(f"json:{jf.name}", False, "unreadable JSON")
        for jf in sorted(raw.glob("g4_*.json")):
            try:
                audit_g4_json(jf, json.loads(jf.read_text(encoding="utf-8")), audit, devices)
            except json.JSONDecodeError:
                audit.check(f"json:{jf.name}", False, "unreadable JSON")
        # hardware consistency: every GPU record on this machine saw the same device
        if len(devices) > 1:
            audit.check("hardware-consistency", False,
                        f"records claim DIFFERENT GPUs: {sorted(devices)} — "
                        "claimed hardware must match actual hardware")
        else:
            audit.check("hardware-consistency", True,
                        f"single device across all records: {next(iter(devices), None)}")

    # 3. gate reports: PASS verdicts must reference non-empty raw artifacts
    reports = root / "windows-training-validation" / "reports"
    if reports.is_dir():
        for jf in sorted(reports.glob("G1_MATRIX_*.json")):
            d = json.loads(jf.read_text(encoding="utf-8"))
            if d.get("verdict") == "PASS":
                legs = d.get("legs") or []
                audit.check(f"matrix-has-legs:{jf.name}", bool(legs), "PASS verdict with zero legs")

    # 4. no unsupported official-support language in new-phase docs
    doc_dirs = ["release-provenance", "windows-training-validation", "amp-rca",
                "upstream-readiness", "platform-matrix", "docs/release-closure"]
    for dr in doc_dirs:
        for mf in (root / dr).rglob("*.md"):
            text = mf.read_text(encoding="utf-8", errors="replace")
            for pat in OFFICIAL_PATTERNS:
                if re.search(pat, text, re.IGNORECASE):
                    audit.check(f"official-claim:{mf.name}", False, f"matches {pat!r}")

    # 5. baseline state JSON parses and pins the frozen head
    bs = root / "docs" / "release-closure" / "BASELINE_STATE.json"
    if bs.is_file():
        try:
            d = json.loads(bs.read_text(encoding="utf-8"))
            audit.check("baseline-head", d.get("repo_head_at_audit", "").startswith("f9f745e"),
                        "baseline head mismatch")
        except json.JSONDecodeError:
            audit.check("baseline-json", False, "unreadable")

    # 6. claims ledger: every PASS/PROVEN claim cites at least one existing file
    claims_md = root / "docs" / "release-closure" / "CLAIMS_AND_EVIDENCE.md"
    if claims_md.is_file():
        text = claims_md.read_text(encoding="utf-8", errors="replace")
        ext_pat = re.compile(r"[\w\-/\.{\}*]+\.(?:json|log|csv|md|py|pt|yaml)")
        for line in text.splitlines():
            m = re.match(r"\|\s*(C\d+)\s*\|\s*(.*?)\s*\|\s*(PASS|FAIL|SKIP|BLOCKED|NOT_RUN|EXPECTED_FAIL)\b", line)
            if not m:
                continue
            cid, status = m.group(1), m.group(3)
            evidence_cell = line.rsplit("|", 2)[-2] if line.count("|") >= 3 else ""
            if status in ("PASS", "EXPECTED_FAIL"):
                refs = [r for r in ext_pat.findall(evidence_cell)
                        if not r.startswith("http")]
                paths = []
                for r in refs:
                    cand = root / r
                    if cand.is_file():
                        paths.append(cand)
                    elif "*" in r or "{" in r:
                        # wildcard reference (e.g. g3_amp_*.json) — resolve by glob
                        pattern_dir = r.split("*")[0].rsplit("/", 1)[0] if "/" in r else ""
                        pat = Path(r).name
                        found = list((root / pattern_dir).glob(pat)) if pattern_dir else list(root.rglob(pat))
                        paths.extend(found[:1])
                    elif any(cand_sub.is_file() for cand_sub in root.rglob(Path(r).name)):
                        paths.append(r)  # found elsewhere in repo
                audit.check(f"claim-evidence:{cid}", bool(paths),
                            f"{status} claim cites no existing evidence file: {evidence_cell[:120]!r}")

    # 7. R22A.2.1 P0-B: manifest/SHA256SUMS evidence integrity vs the exact
    #    Git tree — every referenced file must be COMMITTED and hash-match
    audit_git_tree_evidence(root, audit)

    n = len(audit.checks)
    summary = {"ok": audit.ok, "n_checks": n, "n_violations": len(audit.violations),
               "violations": audit.violations,
               "note": "SKIP never counts as PASS; PASS claims require binary+GPU provenance; "
                       "verdicts are recomputed from embedded assertion data"}
    if not args.json_only:
        print(json.dumps(summary, indent=2))
    sys.exit(0 if audit.ok else 1)


if __name__ == "__main__":
    main()
