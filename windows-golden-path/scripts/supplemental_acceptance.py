# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""UNIFIED supplemental acceptance (R22A.4 §5/§6/§9) — ONE shared verdict
implementation for BOTH architectures, CPU-only, fail-closed.

Core rules (the R22A.3 fail-open defects are structurally impossible here):
  - Part A (AdamW+AMP) is ALWAYS recomputed from embedded facts via the
    schema adapters (r22a2-flat / r22a3-nested) into the unified contract —
    a stored pass_fail_skip is never authority.
  - Part B (workers=8 matrix) is ALWAYS recomputed from the frozen runs[]
    facts through run_stability.evaluate_workers_matrix — the serialized
    `workers8_overall` and per-run `status` fields are inputs ONLY; a forged
    stored PASS cannot survive (spoof: workers8_overall.verdict=PASS with
    runs[2].exit_code=1 → recomputed NO_GO).
  - Cache composition is re-derived from home identity: a fresh-home first
    use is CACHE_PRIMING and never counts as pre-warmed; an ADDITIONAL warm
    sample must carry home_pre_existed=true + explicit justification + its
    own run id/log/timestamp.
  - Physical provenance is mandatory per arch (gfx_target match, GPU name
    recorded, runtime_class ceiling); synthetic receipts can never PASS.
  - Dual-arch mode reports each architecture side by side WITHOUT comparing
    dGPU vs APU performance, and distinguishes
    PHYSICAL_TRAINING_FUNCTIONAL_PASS from RELEASE_GRADE_EVIDENCE_ACCEPTED.

Evidence categories consumed (mission §8): raw receipts/logs are
IMMUTABLE_RAW_EVIDENCE (bytes never rewritten); everything this module
emits is DERIVED_RECONCILIATION.

    python supplemental_acceptance.py --arch gfx1151 \
        --part-a evidence/raw/r22a3-gfx1151/R22A3_ADAMW_AMP.json \
        --part-b evidence/raw/r22a3-gfx1151/R22A3_WORKERS8_RUNS.json \
        --additional-runs evidence/raw/r22a3-gfx1151/R22A3_WORKERS8_WARM_ADDITIONAL_RUNS.json \
        --out report.json
    python supplemental_acceptance.py --dual --repo-root . --out dual_arch_acceptance.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402
import audit_adamw_amp as adamw  # noqa: E402
import run_stability as rs  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
GFX_PACKS = {
    "gfx1100": "evidence/raw/r22a2-gfx1100",
    "gfx1151": "evidence/raw/r22a3-gfx1151",
}
ARCH_PASS = {
    "gfx1100": "R22A2_GFX1100_SUPPLEMENTAL_PASS",
    "gfx1151": "R22A3_GFX1151_SUPPLEMENTAL_PASS",
}
CEILING = "DEV_CANDIDATE (maximum runtime classification; never OFFICIAL_STABLE / R23_RELEASE_READY)"


# --- helpers -----------------------------------------------------------------

def _sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _lf_sha(p: Path) -> str:
    """SHA256 of the file's bytes with CRLF normalized to LF — the R22A.3
    runner hashed the logical text before a CRLF-translating write, so the
    frozen raw_log_sha256 values are LF-normalized (recovery reconciles both)."""
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_log_text(path: Path, expected_sha: str | None) -> tuple[str | None, dict]:
    """Load a committed raw log, verifying its authenticity against the frozen
    receipt hash. Three historical hash FORMS are accepted (each era's runner
    hashed a different one — all three are recorded for audit):
      bytes        — sha256 of the committed bytes (byte-exact raw evidence)
      lf-normalized— sha256 after CRLF→LF (R22A.3 runner hashed the logical
                     text before a CRLF-translating write)
      decoded-text — sha256 of utf-8 decode(errors=replace) + re-encode
                     (R22A.2 runner hashed read_text() of logs containing
                     non-UTF-8 bytes, which errors=replace rewrites to U+FFFD)
    """
    if not path or not path.is_file():
        return None, {"log": str(path), "exists": False, "sha_match": False}
    raw = path.read_bytes()
    # universal-newline decoded text (what Path.read_text() yields and what
    # the R22A.2 runner actually hashed: \r\n AND lone \r → \n, invalid bytes
    # → U+FFFD — child logs contain progress-bar \r runs)
    text = raw.decode("utf-8", errors="replace") \
        .replace("\r\n", "\n").replace("\r", "\n")
    b_sha = hashlib.sha256(raw).hexdigest()
    l_sha = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    t_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if expected_sha:
        forms = {"bytes": b_sha, "lf-normalized": l_sha,
                 "universal-newline-text": t_sha}
        form = next((k for k, v in forms.items() if v == expected_sha), None)
        match = form is not None
    else:
        match, form = None, None
    return text, {
        "log": str(path), "exists": True, "sha_match": match,
        "bytes_sha256": b_sha, "lf_sha256": l_sha, "decoded_sha256": t_sha,
        "matched_form": form,
        "note": (f"authentic — frozen receipt hash matches the {form} form"
                 if match else
                 "committed bytes do NOT match the frozen receipt hash "
                 "(no form: bytes / lf-normalized / decoded-text)"),
    }


def concurrency_lower_bound(identities: list[dict]) -> int:
    """Lower bound of simultaneous workers from per-identity first/last-seen
    interval overlap (derived evidence — disclosed, never claimed as a
    measured instantaneous snapshot)."""
    events: list[tuple[float, int]] = []
    for r in identities or []:
        fs, ls = r.get("first_seen"), r.get("last_seen")
        if fs is None or ls is None:
            continue
        events.append((float(fs), 1))
        events.append((float(ls), -1))
    # process interval ENDS before STARTS at equal timestamps (conservative)
    events.sort(key=lambda e: (e[0], e[1]))
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    return mx


# --- Part A recomputation ----------------------------------------------------

def detect_part_a_schema(rec: dict) -> str:
    if "optimizer_steps" in rec or "optim" in rec:
        return "r22a3-nested"
    if "training_counts" in rec or "optimizer" in rec:
        return "r22a2-flat"
    if "optimizer_requested" in rec or "confirmed_update_events" in rec:
        return "unified-flat"
    return "unknown"


def recompute_part_a(rec: dict) -> dict:
    """Recompute Part A's verdict from embedded facts via explicit versioned
    adapters; never trust the stored pass_fail_skip."""
    try:
        schema = detect_part_a_schema(rec)
        if schema == "r22a3-nested":
            facts = adamw.flat_facts_from_r22a3_record(rec)
        elif schema == "r22a2-flat":
            facts = adamw.flat_facts_from_r22a2_record(rec)
        elif schema == "unified-flat":
            facts = dict(rec)  # already the unified flat facts
        else:
            return {"verdict": "REJECTED",
                    "failure_classification": "UNKNOWN_PART_A_SCHEMA",
                    "schema": schema}
        out = adamw.evaluate_adamw_contract(facts)
        out["schema"] = schema
        out["adapter"] = facts.get("_adapter")
        return out
    except Exception as e:  # malformed record can never pass
        return {"verdict": "REJECTED",
                "failure_classification": f"MALFORMED_PART_A({type(e).__name__}: {e})"}


# --- Part B run-record adapters ----------------------------------------------

def _base_run_record(r: dict, **over) -> dict:
    rec = {
        "run": r.get("run"),
        "run_id": r.get("run_id") or f"{r.get('matrix', 'm')}-run{r.get('run')}",
        "exit_code": r.get("exit_code"),
        "cache_class": r.get("cache_class"),
        "cache_expectation": r.get("cache_expectation"),
        "home_dir": r.get("home_dir"),
        "home_pre_existed": r.get("home_pre_existed"),
        "sample_class": r.get("sample_class") or "original",
        "justification": r.get("justification"),
        "requested_workers": r.get("requested_workers"),
        "resolved_num_workers": r.get("resolved_num_workers"),
        "distinct_worker_identities": r.get("distinct_worker_identities"),
        "worker_identities": r.get("worker_identities"),
        "peak_concurrent_workers": r.get("peak_concurrent_workers"),
        "concurrency_lower_bound_derived": r.get("concurrency_lower_bound_derived"),
        "monitor_health": r.get("monitor_health"),
        "independent_lifecycle_corroboration":
            r.get("independent_lifecycle_corroboration"),
        "lingering_after_parent_exit": r.get("lingering_after_parent_exit"),
        "orphan_workers_alive": r.get("orphan_workers_alive"),
        "training_completed": r.get("training_completed"),
        "checkpoint_exists": r.get("checkpoint_exists"),
        "checkpoint_path": r.get("checkpoint_path"),
        "gpu_name": r.get("gpu_name") or r.get("device_name"),
        "torch": r.get("torch"),
        "started_utc": r.get("started_utc") or r.get("start_utc"),
        "log_sha256": r.get("log_sha256") or r.get("raw_log_sha256"),
        "log_text": r.get("log_text"),
        "child_has_main_guard": r.get("child_has_main_guard"),
    }
    rec.update(over)
    return rec


def runs_from_r22a3_receipt(part_b: dict, repo_root: Path,
                            lifecycle_path: Path | None = None,
                            log_dir: Path | None = None) -> list[dict]:
    """Adapt frozen R22A3 (gfx1151) run records to the unified schema.

    The frozen receipts lack monitor-health state (historical harness) — the
    committed PROCESS_LIFECYCLE.json provides INDEPENDENT corroboration, and
    per-run child logs are loaded from the recovered raw pack with SHA
    verification against each run's frozen raw_log_sha256.
    """
    repo_root = Path(repo_root)
    lifecycle = {}
    if lifecycle_path and Path(lifecycle_path).is_file():
        try:
            lc = json.loads(Path(lifecycle_path).read_text(encoding="utf-8"))
            lifecycle = lc.get("runs", {}) if isinstance(lc.get("runs"), dict) else {}
        except Exception:
            lifecycle = {}
    log_dir = Path(log_dir) if log_dir else \
        repo_root / "evidence/raw/r22a3-gfx1151/runs"
    out = []
    raw_runs = part_b.get("runs", []) if isinstance(part_b, dict) else part_b
    for r in raw_runs:
        rid = r.get("run_id")
        lc = lifecycle.get(rid) or {}
        idents = []
        for d in lc.get("descendants", []):
            ct = d.get("create_time")
            idents.append({
                "identity": f"{d.get('pid')}@{ct}" if ct else f"{d.get('pid')}@?",
                "pid": d.get("pid"), "create_time": ct, "ppid": d.get("ppid"),
                "name": d.get("name"), "first_seen": d.get("first_seen"),
                "last_seen": d.get("last_seen"), "sightings": d.get("sightings", 0),
            })
        corrob = None
        if idents:
            sights = [i["sightings"] for i in idents]
            corrob = {
                "source": str(Path(lifecycle_path).relative_to(repo_root)
                              if lifecycle_path else "R22A3_PROCESS_LIFECYCLE.json"),
                "distinct_identities": len(idents),
                "total_sightings": sum(sights),
                "min_per_identity_sightings": min(sights),
                "all_have_create_time": all(i["create_time"] for i in idents),
                "all_have_ppid": all(i["ppid"] is not None for i in idents),
            }
        shutdown = r.get("worker_shutdown")
        lingering = [] if shutdown == "CLEAN" else \
            ([f"orphans:{shutdown}"] if shutdown else None)
        idx = r.get("run")
        log_path = log_dir / f"r22a3_child_run{idx:02d}.log"
        log_text, log_ver = load_log_text(log_path, r.get("raw_log_sha256"))
        rec = _base_run_record(
            r,
            cache_expectation="cold" if "cold(" in str(r.get("cache_class")) else "warm",
            home_dir=r.get("userprofile_env") or r.get("home_dir"),
            home_pre_existed=r.get("home_pre_existed"),  # absent in frozen receipts
            distinct_worker_identities=(lc.get("distinct_worker_pids")
                                        if lc else r.get("distinct_worker_pids")),
            worker_identities=idents,
            concurrency_lower_bound_derived=concurrency_lower_bound(idents) if idents else None,
            peak_concurrent_workers=None,  # not recorded by the frozen harness
            monitor_health=None,  # historical harness pre-dates health state
            independent_lifecycle_corroboration=corrob,
            lingering_after_parent_exit=lingering,
            orphan_workers_alive=(0 if lingering == [] else
                                  (len(lingering) if lingering else None)),
            training_completed=r.get("training_completed"),
            checkpoint_exists=r.get("checkpoint_exists"),
            gpu_name=r.get("device_name"),
            started_utc=r.get("start_utc"),
            log_sha256=r.get("raw_log_sha256"),
            log_text=log_text,
            child_has_main_guard=True,  # verified structurally at run time (frozen log)
            _log_verification=log_ver,
        )
        out.append(rec)
    return out


def runs_from_unified_receipt(receipt, log_dir: Path | None) -> list[dict]:
    """Adapt unified-runner runs (additional samples etc.). The runner strips
    log_text from slim records — committed child logs are loaded with SHA
    verification when log_dir is given; embedded log_text wins if present."""
    runs = receipt.get("runs") if isinstance(receipt, dict) else receipt
    out = []
    for r in runs or []:
        over = {}
        if r.get("matrix") is None and str(r.get("sample_class") or "") == "additional":
            # keep matrix/run identity distinct from original-matrix runs
            over["matrix"] = "additional"
        if r.get("log_text"):
            out.append(_base_run_record(r, **over))
            continue
        idx = r.get("run")
        log_text, ver = None, {"log": None, "exists": False, "sha_match": None}
        if log_dir is not None and idx is not None:
            exp_sha = r.get("log_sha256") or r.get("raw_log_sha256")
            cands = [Path(log_dir) / f"run{idx:02d}" / "child.log"] + \
                sorted(Path(log_dir).glob(f"*run{idx:02d}*.log")) + \
                sorted(Path(log_dir).glob("*additional*.log"))
            fallback = None
            for c in cands:
                if not c.is_file():
                    continue
                txt, v = load_log_text(c, exp_sha)
                if v.get("sha_match") is True:
                    log_text, ver = txt, v  # SHA decides, not name order
                    break
                if fallback is None:
                    fallback = (txt, v)
            if log_text is None and fallback is not None:
                log_text, ver = fallback
        out.append(_base_run_record(r, log_text=log_text,
                                    _log_verification=ver, **over))
    return out


def runs_from_r22a2_pack(repo_root: Path) -> list[dict]:
    """Adapt frozen R22A2 (gfx1100) matrix runs (+ additional sample) to the
    unified schema. Source: committed runs/{cold,warm,additional}_matrix_
    stability_runs.json + committed child logs (SHA-verified)."""
    repo_root = Path(repo_root)
    pack = repo_root / "evidence/raw/r22a2-gfx1100"
    out = []
    for matrix, fname in (("cold", "cold_matrix_stability_runs.json"),
                          ("warm", "warm_matrix_stability_runs.json"),
                          ("additional", "additional_matrix_stability_runs.json")):
        p = pack / "runs" / fname
        if not p.is_file():
            continue
        try:
            runs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in runs:
            idx = r.get("run")
            log_path = pack / "runs" / f"{matrix}_run{idx:02d}_child.log"
            log_text, log_ver = load_log_text(log_path, r.get("log_sha256"))
            pids = r.get("worker_pids_observed") or []
            idents = [{"identity": f"{pid}@?", "pid": pid, "create_time": None,
                       "first_seen": None, "last_seen": None, "sightings": None}
                      for pid in pids]
            out.append(_base_run_record(
                r,
                matrix=matrix,
                run_id=f"R22A2-{matrix}-run{idx:02d}",
                sample_class=("additional" if matrix == "additional" else "original"),
                justification=(
                    "R22A.2.1 P0-D: strict contract requires exactly 3 qualifying "
                    "pre-warmed runs; the frozen matrix supplies 2 — ONE additional "
                    "short warm run on the retained shared home (committed hardened "
                    "harness c07aa9b)" if matrix == "additional" else None),
                distinct_worker_identities=len(pids) if pids else None,
                worker_identities=idents,
                peak_concurrent_workers=r.get("peak_concurrent_workers"),
                concurrency_lower_bound_derived=None,
                monitor_health=None,
                independent_lifecycle_corroboration=(
                    {"source": f"runs/{fname}",
                     "distinct_identities": len(pids),
                     "total_sightings": r.get("monitor_samples"),
                     "monitor_samples": r.get("monitor_samples"),
                     "note": "peak_concurrent recorded by CIM snapshot monitor"}
                    if r.get("monitor_samples") else None),
                log_text=log_text,
                _log_verification=log_ver,
            ))
    return out


# --- verdicts ----------------------------------------------------------------

def evaluate_part_b(runs: list[dict], gpu_name: str | None,
                    expected_cold: int = 2, expected_warm: int = 3,
                    child_guard: bool = True) -> dict:
    """Recompute the workers=8 matrix verdict from run FACTS (never a stored
    overall). Log authenticity problems fail closed."""
    problems = []
    for r in runs:
        ver = (r.get("_log_verification") or {})
        if ver.get("exists") and ver.get("sha_match") is False:
            problems.append(f"run {r.get('run_id')}: committed log bytes do not "
                            "match the frozen receipt hash")
    matrix = rs.evaluate_workers_matrix({
        "runs": runs,
        "child_has_main_guard": child_guard,
        "gpu_name": gpu_name,
        "expected_cold": expected_cold,
        "expected_warm": expected_warm,
    })
    if problems:
        if matrix["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS":
            matrix = {**matrix, "verdict": "NO_GO",
                      "reason": "; ".join(problems)}
        matrix["log_authenticity"] = problems
    matrix["derived_cache_roles"] = [r["cache_role"] for r in rs.assign_cache_roles(runs)]
    return matrix


def physical_provenance_ok(rec: dict, gfx_expected: str) -> tuple[bool, str | None]:
    if not rec.get("gpu_name"):
        return False, "no gpu_name recorded (synthetic receipt cannot claim physical GPU)"
    if rec.get("gfx_target") != gfx_expected:
        return False, f"gfx_target {rec.get('gfx_target')!r} != {gfx_expected}"
    rc = rec.get("runtime_class")
    if rc in ("ENGINEERING_REFERENCE", "INCONCLUSIVE", None):
        return False, f"runtime_class {rc!r} cannot earn a physical PASS"
    return True, None


# --- runtime provenance gate (mission R22A.4.1 §5) ----------------------------

def _therock_revision(version: str) -> str | None:
    """TheRock source revision carried by a DEV local version, e.g.
    '2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-ff5769655eeb…' -> the trailing hex
    segment (whichever of '-'/'.'
    separates it). Official-stable versions ('2.12.0+rocm7.14.1') carry no
    such revision -> None."""
    tail = version.split("+", 1)[-1]
    for seg in reversed(tail.replace("-", ".").split(".")):
        if len(seg) >= 8 and all(c in "0123456789abcdef" for c in seg.lower()):
            return seg.lower()
    return None


def runtime_provenance_gate(receipt: dict, package_lock: dict | None,
                            package_lock_sha256: str | None,
                            reference: dict) -> dict:
    """Fail-closed provenance classification for a receipt whose
    runtime_class is INCONCLUSIVE — the R22A4-B-ADD1 case: the probe did not
    pass --channel, so the receipt cannot self-classify its channel.

    Authority chain (mission R22A.4.1 §5.2): the receipt field is NEVER
    rewritten (quoted verbatim); classification authority is the INDEPENDENTLY
    HASHED committed DEV package lock plus full runtime-identity agreement
    with the frozen same-pack receipts (reference). Fail-closed policy:
      - absent evidence (lock/lock-hash/identity component missing)
        -> INCONCLUSIVE, never accepted;
      - conflicting or forged evidence (hash mismatch, wrong wheel/DLL/gfx,
        mixed stable+DEV identity, non-dev lock) -> NO_GO;
      - everything verified -> PROVENANCE_ACCEPTED_DEV (ceiling DEV_CANDIDATE).
    """
    problems: list[str] = []
    missing: list[str] = []
    checks: dict[str, str] = {}

    def pkg(name: str) -> dict | None:
        for e in (package_lock or {}).get("packages") or []:
            if e.get("name") == name:
                return e
        return None

    # 1. authoritative package provenance (committed lock vs receipt claim)
    if package_lock is None or not package_lock_sha256:
        lock_state = "LOCK_ABSENT"
        missing.append("committed package lock or its sha256 not provided")
    elif receipt.get("wheel_lock_sha256") != package_lock_sha256:
        lock_state = "LOCK_MISMATCH"
        problems.append(f"receipt wheel_lock_sha256 "
                        f"{str(receipt.get('wheel_lock_sha256'))[:12]}… != committed "
                        f"package-lock hash {str(package_lock_sha256)[:12]}…")
    elif str(package_lock.get("channel") or "") != "dev":
        lock_state = "LOCK_NOT_DEV"
        problems.append(f"package-lock channel {package_lock.get('channel')!r} != 'dev'")
    else:
        lock_state = "DEV_LOCK_VERIFIED"
    checks["package_lock"] = lock_state

    # 2. runtime identity match against the frozen reference receipts
    def identity(field: str, got, want) -> None:
        if want is None or got in (None, ""):
            missing.append(f"{field} not recorded (receipt={got!r}, reference={want!r})")
            checks[field] = "UNVERIFIABLE"
        elif got != want:
            problems.append(f"{field}: receipt {got!r} != reference {want!r}")
            checks[field] = "MISMATCH"
        else:
            checks[field] = "MATCH"

    identity("torch", receipt.get("torch"), reference.get("torch"))
    identity("ultralytics", receipt.get("ultralytics"),
             reference.get("ultralytics"))
    identity("loaded_miopen_dll_sha256", receipt.get("loaded_miopen_dll_sha256"),
             reference.get("loaded_miopen_dll_sha256"))
    identity("gfx_target", receipt.get("gfx_target"), reference.get("gfx_target"))
    if not receipt.get("gpu_name"):
        problems.append("no gpu_name recorded (synthetic receipt cannot claim "
                        "physical GPU)")
        checks["gpu_name"] = "MISSING"
    else:
        checks["gpu_name"] = "RECORDED"

    # 3. wheel identity consistency WITHIN the verified lock (forged-label and
    #    mixed stable/DEV classes): the receipt's torch must BE the lock's
    #    torch wheel (a '-'/'.'
    #    before the TheRock revision is a runner/lock spelling difference, not
    #    an identity difference) and receipt torch, lock torch and lock rocm
    #    must all carry the SAME TheRock revision.
    if lock_state == "DEV_LOCK_VERIFIED":
        lock_torch = str((pkg("torch") or {}).get("version") or "")
        lock_rocm = str((pkg("rocm") or {}).get("version") or "")
        rev_receipt = _therock_revision(str(receipt.get("torch") or ""))
        rev_lock_torch = _therock_revision(lock_torch)
        rev_lock_rocm = _therock_revision(lock_rocm)
        if not lock_torch or not rev_receipt or not rev_lock_rocm:
            missing.append(f"wheel identity unverifiable (receipt torch "
                           f"{str(receipt.get('torch'))[:40]!r}, lock torch "
                           f"{lock_torch[:40]!r}, lock rocm {lock_rocm[:40]!r})")
            checks["wheel_identity"] = "UNVERIFIABLE"
        elif (str(receipt.get("torch")).replace("-", ".", 1) != lock_torch
              or rev_receipt != rev_lock_rocm or rev_lock_torch != rev_lock_rocm):
            problems.append(f"wheel identity mismatch: receipt torch "
                            f"{str(receipt.get('torch'))[:40]!r} vs lock torch "
                            f"{lock_torch[:40]!r} / lock rocm {lock_rocm[:40]!r} "
                            f"(mixed stable/DEV or forged DEV label)")
            checks["wheel_identity"] = "MISMATCH"
        else:
            checks["wheel_identity"] = "MATCH"

    if problems:
        disposition, match_state = "NO_GO", {"mismatch": problems}
    elif missing:
        disposition, match_state = "INCONCLUSIVE", {"unverifiable": missing}
    else:
        disposition, match_state = "PROVENANCE_ACCEPTED_DEV", "MATCH"
    return {
        "run_id": receipt.get("run_id"),
        "RECEIPT_RUNTIME_CLASS": receipt.get("runtime_class"),  # verbatim, never rewritten
        "AUTHORITATIVE_PACKAGE_PROVENANCE": lock_state,
        "RUNTIME_IDENTITY_MATCH": match_state,
        "identity_checks": checks,
        "ACCEPTANCE_DISPOSITION": disposition,
        "ceiling": "DEV_CANDIDATE",
        "note": "receipt runtime_class is preserved verbatim; acceptance for an "
                "INCONCLUSIVE receipt flows ONLY from the committed DEV package "
                "lock hash + full runtime-identity agreement with the frozen "
                "same-pack receipts (fail-closed: absent->INCONCLUSIVE, "
                "conflicting->NO_GO)",
    }


def combined_verdict(part_a: dict, part_b_runs: list[dict], gfx_expected: str,
                     part_b_gpu_name: str | None = None,
                     expected_cold: int = 2, expected_warm: int = 3,
                     child_guard: bool = True,
                     monitor_exception_disclosure: dict | None = None) -> dict:
    """Pure per-architecture supplemental verdict (CPU-testable)."""
    reasons: list[str] = []
    a = recompute_part_a(part_a)
    a_ok = a["verdict"] == "ADAMW_AMP_MULTISTEP_PASS"
    if not a_ok:
        reasons.append(f"PartA {a['verdict']}/{a.get('failure_classification')}")
    b = evaluate_part_b(part_b_runs, part_b_gpu_name or part_a.get("gpu_name"),
                        expected_cold, expected_warm, child_guard)
    b_ok = b["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS"
    if not b_ok:
        reasons.append(f"PartB {b.get('verdict')}: {b.get('reason')}")
    prov_a, pa_reason = physical_provenance_ok(part_a, gfx_expected)
    if not prov_a:
        reasons.append(f"PartA provenance: {pa_reason}")

    if a_ok and b_ok and prov_a:
        verdict = ARCH_PASS[gfx_expected]
    elif a_ok != b_ok:
        verdict = "PARTIAL_PASS"
    else:
        verdict = "NO-GO"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "part_a_recomputed": {"verdict": a["verdict"],
                              "failure_classification": a.get("failure_classification"),
                              "schema": a.get("schema"),
                              "adapter": a.get("adapter"),
                              "checks": a.get("checks")},
        "part_b_overall": {"verdict": b["verdict"], "reason": b.get("reason"),
                           "derived_cache_roles": b.get("derived_cache_roles"),
                           "log_authenticity": b.get("log_authenticity")},
        "monitor_exception_disclosure": monitor_exception_disclosure,
        "runtime_ceiling": CEILING,
    }


# --- dual-arch reconciliation (mission §9) ------------------------------------

def _arch_facts(part_a: dict, part_b_runs: list[dict], b_verdict: dict) -> dict:
    a = recompute_part_a(part_a)
    schema = a.get("schema")
    if schema == "r22a3-nested":
        fa = adamw.flat_facts_from_r22a3_record(part_a)
    elif schema == "r22a2-flat":
        fa = adamw.flat_facts_from_r22a2_record(part_a)
    else:  # unified-flat facts are already canonical
        fa = dict(part_a)
    tc = part_a.get("training_counts") or {}
    steps = part_a.get("optimizer_steps") or {}
    return {
        "gpu_architecture": part_a.get("gfx_target"),
        "gpu_name": part_a.get("gpu_name"),
        "runtime_class": part_a.get("runtime_class"),
        "adamw_auto_selected": (fa.get("optimizer_requested") == "auto"
                                and fa.get("optimizer_class") == "AdamW"),
        "autocast_forward": (f"{fa.get('autocast_forward_on')}/"
                             f"{fa.get('autocast_forward_samples')}"),
        "low_precision_dtype_observed": fa.get("low_precision_dtype"),
        "low_precision_op_samples": fa.get("low_precision_op_samples"),
        "step_attempts": (fa.get("optimizer_steps_underlying")
                          or steps.get("attempted_invocations")),
        "effective_updates": (fa.get("confirmed_update_events")
                              or steps.get("effective_updates_sentinel_proven")),
        "nonfinite_skip_or_backoff": (part_a.get("gradscaler") or {}).get(
            "backoff_events_observed",
            (part_a.get("gradscaler") or {}).get("scale_backoff_events_observed")),
        "named_param_delta": (f"{adamw.changed_tensors(part_a.get('raw_trainer_model_delta') or {})}/"
                              f"{(part_a.get('raw_trainer_model_delta') or {}).get('total_tensors')}"),
        "workers_configured": (part_b_runs[0].get("requested_workers")
                               if part_b_runs else None),
        "worker_identities_observed": (
            part_b_runs[0].get("distinct_worker_identities") if part_b_runs else None),
        "runs_in_matrix": len(part_b_runs),
        "derived_cache_roles": b_verdict.get("derived_cache_roles"),
        "monitor_health": ("recorded" if any(r.get("monitor_health") for r in part_b_runs)
                           else "independent-corroboration"
                           if any(r.get("independent_lifecycle_corroboration")
                                  for r in part_b_runs) else "unrecorded"),
        "part_a_verdict": a["verdict"],
        "part_b_verdict": b_verdict.get("verdict"),
    }


def dual_arch_acceptance(a1100: dict, runs1100: list, a1151: dict, runs1151: list,
                         b1100: dict, b1151: dict,
                         monitor_disclosures: dict | None = None,
                         additional_provenance: dict | None = None) -> dict:
    """Side-by-side dual-arch reconciliation. Every displayed value is
    recomputed from the corresponding source records (mission §9); nothing is
    a template. PHYSICAL_TRAINING_FUNCTIONAL_PASS (the hardware trained) is
    explicitly distinguished from RELEASE_GRADE_EVIDENCE_ACCEPTED (the
    evidence satisfies the strict release contract).

    additional_provenance: result of runtime_provenance_gate() for the
    INCONCLUSIVE-classified additional sample. When supplied and any
    additional-class run participates in a matrix, acceptance FAILS CLOSED
    unless the disposition is PROVENANCE_ACCEPTED_DEV (mission R22A.4.1 §5).
    None preserves the historical pure-function behavior (CPU-test call
    path); the canonical CLI path always evaluates the gate."""
    c1100 = combined_verdict(a1100, runs1100, "gfx1100", a1100.get("gpu_name"))
    c1151 = combined_verdict(a1151, runs1151, "gfx1151", a1151.get("gpu_name"))
    f1100 = _arch_facts(a1100, runs1100, c1100["part_b_overall"])
    f1151 = _arch_facts(a1151, runs1151, c1151["part_b_overall"])

    for runs, c in ((runs1100, c1100), (runs1151, c1151)):
        if (additional_provenance is not None
                and any(str(r.get("sample_class") or "") == "additional" for r in runs)
                and additional_provenance.get("ACCEPTANCE_DISPOSITION")
                != "PROVENANCE_ACCEPTED_DEV"):
            why = additional_provenance.get("ACCEPTANCE_DISPOSITION") or "GATE_NOT_EVALUATED"
            c["verdict"] = "NO-GO"
            c["reasons"] = c["reasons"] + [
                f"additional-sample runtime provenance gate: {why} "
                f"({additional_provenance.get('RUNTIME_IDENTITY_MATCH')}, "
                f"lock={additional_provenance.get('AUTHORITATIVE_PACKAGE_PROVENANCE')})"]

    def functional(f: dict, c: dict, runs: list) -> str:
        trained_clean = (f["part_a_verdict"] == "ADAMW_AMP_MULTISTEP_PASS"
                         and bool(runs)
                         and all(r.get("exit_code") == 0 for r in runs)
                         and all(r.get("training_completed") or
                                 "STABILITY_CHILD_DONE" in str(r.get("log_text"))
                                 for r in runs))
        return "PHYSICAL_TRAINING_FUNCTIONAL_PASS" if trained_clean else "NOT_ESTABLISHED"

    def evidence_grade(c: dict) -> str:
        return "RELEASE_GRADE_EVIDENCE_ACCEPTED" if c["verdict"].endswith(
            "SUPPLEMENTAL_PASS") else "NOT_ACCEPTED"

    validated = (c1100["verdict"] == ARCH_PASS["gfx1100"]
                 and c1151["verdict"] == ARCH_PASS["gfx1151"])
    return {
        "mission": "R22A.4",
        "verdict": "R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED" if validated else "NO-GO",
        "verdict_ceiling": CEILING,
        "gfx1100": {"facts": f1100, "combined": c1100,
                    "physical_training_functional": functional(f1100, c1100, runs1100),
                    "release_grade_evidence": evidence_grade(c1100)},
        "gfx1151": {"facts": f1151, "combined": c1151,
                    "physical_training_functional": functional(f1151, c1151, runs1151),
                    "release_grade_evidence": evidence_grade(c1151)},
        "monitor_exception_disclosures": monitor_disclosures or {},
        "additional_sample_provenance": additional_provenance,
        "notes": [
            "every cell recomputed from frozen raw records via versioned adapters",
            "cache roles derived from home identity only (fresh-home first use = "
            "CACHE_PRIMING, never pre-warmed)",
            "no dGPU vs APU performance comparison is made or implied",
            "effective-update counts (6 gfx1100 / 7 gfx1151) are factual "
            "observations of different hardware runs, not targets",
            "additional-sample (INCONCLUSIVE receipt) acceptance flows only "
            "from the committed DEV package-lock hash + runtime identity "
            "match (runtime_provenance_gate); the receipt's own "
            "runtime_class field is preserved verbatim",
        ],
    }


# --- CLI ----------------------------------------------------------------------

def dual_input_evidence(root: Path) -> list[dict]:
    """Deterministic identity of every evidence file the --dual recompute
    reads: repo-relative path + SHA256 of the COMMITTED blob (git cat-file at
    HEAD — the worktree copy is never authority)."""
    p1100 = root / GFX_PACKS["gfx1100"]
    p1151 = root / GFX_PACKS["gfx1151"]
    rels = [f"{GFX_PACKS['gfx1100']}/R22A2_ADAMW_AMP.json"]
    for f in ("cold_matrix_stability_runs.json", "warm_matrix_stability_runs.json",
              "additional_matrix_stability_runs.json"):
        rels.append(f"{GFX_PACKS['gfx1100']}/runs/{f}")
    rels += [p.relative_to(root).as_posix()
             for p in sorted((p1100 / "runs").glob("*child.log"))]
    rels += [f"{GFX_PACKS['gfx1151']}/{f}" for f in (
        "R22A3_ADAMW_AMP.json", "R22A3_WORKERS8.json", "R22A3_WORKERS8_RUNS.json",
        "R22A3_PROCESS_LIFECYCLE.json", "R22A3_WORKERS8_WARM_ADDITIONAL.json",
        "R22A3_WORKERS8_WARM_ADDITIONAL_RUNS.json")]
    rels += [p.relative_to(root).as_posix()
             for p in sorted((p1151 / "runs").glob("*.log"))]
    rels.append("evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json")
    out = []
    for rel in rels:
        try:
            blob = subprocess.run(
                ["git", "cat-file", "blob", f"HEAD:{rel}"], cwd=str(root),
                capture_output=True, timeout=30).stdout
        except Exception:
            blob = b""
        out.append({"path": rel,
                    "git_blob_sha256": hashlib.sha256(blob).hexdigest()
                    if blob else None})
    return out


def dual_harness_code_sha(root: Path) -> dict:
    """SHA256 of the harness sources that PRODUCED this report — hashed as
    COMMITTED BLOBS (git cat-file at HEAD), never as working-tree bytes:
    a CRLF checkout must not change the recorded identity. Falls back to
    LF-normalized working bytes when git is unavailable."""
    here = Path(__file__).resolve().parent
    root = Path(root).resolve()
    out = {}
    for n in ("supplemental_acceptance.py", "run_stability.py",
              "audit_adamw_amp.py", "gp_lib.py"):
        rel = (here / n).resolve().relative_to(root).as_posix()
        try:
            blob = subprocess.run(
                ["git", "cat-file", "blob", f"HEAD:{rel}"], cwd=str(root),
                capture_output=True, timeout=30).stdout
        except Exception:
            blob = b""
        if blob:
            out[n] = hashlib.sha256(blob).hexdigest()
        else:
            out[n] = hashlib.sha256(
                (here / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return out


def _load(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arch", choices=["gfx1100", "gfx1151"], default=None)
    ap.add_argument("--dual", action="store_true",
                    help="dual-arch reconciliation from canonical evidence packs")
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--part-a", default=None)
    ap.add_argument("--part-b", default=None,
                    help="part-B receipt containing runs[] (r22a3) or pack dir (r22a2)")
    ap.add_argument("--additional-runs", default=None,
                    help="additional-sample runs json (unified/compat runner output)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="R22A4-ACCEPT")
    args = ap.parse_args()

    root = Path(args.repo_root)
    if args.dual:
        p1100 = root / GFX_PACKS["gfx1100"]
        p1151 = root / GFX_PACKS["gfx1151"]
        a1100 = _load(p1100 / "R22A2_ADAMW_AMP.json")
        a1151 = _load(p1151 / "R22A3_ADAMW_AMP.json")
        runs1100 = runs_from_r22a2_pack(root)
        part_b1151 = _load(p1151 / "R22A3_WORKERS8_RUNS.json")
        runs1151 = runs_from_r22a3_receipt(
            part_b1151, root,
            lifecycle_path=p1151 / "R22A3_PROCESS_LIFECYCLE.json")
        add_path = p1151 / "R22A3_WORKERS8_WARM_ADDITIONAL_RUNS.json"
        if add_path.is_file():
            runs1151 += runs_from_unified_receipt(_load(add_path), p1151 / "runs")
        disc = {"gfx1151": {
            "found_in": "evidence/raw/r22a3-gfx1151/R22A3_WORKERS8.log",
            "classified_as": rs.MONITOR_EXIT_RACE,
            "raw_exception": "psutil.NoSuchProcess (pre-R22A.4 harness revision)",
            "affected_runs": ["R22A3-B-R1"],
            "disposition": "function-level training PASS preserved: independent "
                           "per-run identity/sighting evidence (13 identities × "
                           "33–148 sightings, all with ppid+create_time) "
                           "substantiates all five runs; the sampler-thread death "
                           "is disclosed, not deleted; R22A.4 harness records "
                           "monitor health explicitly and fails closed",
        }} if (p1151 / "R22A3_WORKERS8_RUNS.json").is_file() else {}
        # Runtime provenance gate (mission R22A.4.1 §5): the additional
        # sample's receipt is INCONCLUSIVE (no --channel at probe time); its
        # DEV identity is established ONLY through the committed package lock
        # (hash-verified against the Git blob content on disk) + runtime
        # identity agreement with the frozen same-pack receipts.
        additional_provenance = None
        add_receipt_path = p1151 / "R22A3_WORKERS8_WARM_ADDITIONAL.json"
        lock_path = root / "evidence/raw/r22a-gfx1151/R22A_GFX1151_PACKAGE_LOCK.json"
        if add_path.is_file() and add_receipt_path.is_file():
            frozen = _load(p1151 / "R22A3_WORKERS8.json")
            additional_provenance = runtime_provenance_gate(
                _load(add_receipt_path),
                _load(lock_path) if lock_path.is_file() else None,
                _sha_file(lock_path) if lock_path.is_file() else None,
                reference={
                    "torch": frozen.get("torch"),
                    "ultralytics": frozen.get("ultralytics"),
                    "loaded_miopen_dll_sha256": a1151.get("loaded_miopen_dll_sha256"),
                    "gfx_target": frozen.get("gfx_target"),
                    "gpu_name": frozen.get("gpu_name"),
                })
        b1100 = evaluate_part_b(runs1100, a1100.get("gpu_name"))
        b1151 = evaluate_part_b(runs1151, a1151.get("gpu_name"))
        rep = dual_arch_acceptance(a1100, runs1100, a1151, runs1151, b1100, b1151,
                                   disc, additional_provenance)
        # self-describing provenance (mission R22A.4.1 §6): exact input
        # evidence identity (committed blobs) + harness code identity +
        # adapter versions. No timestamp: the dual report stays deterministic.
        rep["input_evidence"] = dual_input_evidence(root)
        rep["harness_code_sha256"] = dual_harness_code_sha(root)
        rep["schema_adapters"] = {
            arch: rep[arch]["combined"]["part_a_recomputed"].get("adapter")
            for arch in ("gfx1100", "gfx1151")}
    else:
        if not args.arch or not args.part_a or not args.part_b:
            ap.error("--arch, --part-a and --part-b are required (or use --dual)")
        part_a = _load(args.part_a)
        if args.arch == "gfx1151":
            part_b = _load(args.part_b)
            runs = runs_from_r22a3_receipt(
                part_b, root,
                lifecycle_path=root / GFX_PACKS["gfx1151"] / "R22A3_PROCESS_LIFECYCLE.json")
            if args.additional_runs:
                add_log_dir = root / GFX_PACKS["gfx1151"] / "runs"
                runs += runs_from_unified_receipt(_load(args.additional_runs), add_log_dir)
            gpu_b = part_b.get("gpu_name") if isinstance(part_b, dict) else None
        else:
            runs = runs_from_r22a2_pack(root)
            gpu_b = part_a.get("gpu_name")
        rep = {
            "run_id": args.run_id, "mission": "R22A.4",
            "timestamp": gp_lib.now_utc(),
            "arch": args.arch,
            "part_a_record": str(args.part_a),
            "part_b_record": str(args.part_b),
            "combined": combined_verdict(part_a, runs, args.arch, gpu_b),
            "pass_fail_skip": None,
            "note": "combined verdict recomputed from embedded facts of the evidence "
                    "records via versioned adapters; claimed verdicts are inputs "
                    "only, never authority",
        }
        rep["pass_fail_skip"] = rep["combined"]["verdict"]

    # newline="\n" keeps the committed report bytes hash-identical across
    # platforms (no CRLF translation on Windows — same convention the runner
    # uses for child logs)
    Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False,
                                         default=repr), encoding="utf-8",
                                         newline="\n")
    verdict = rep.get("verdict") or rep.get("combined", {}).get("verdict")
    print(json.dumps({"verdict": verdict} if args.dual else rep["combined"],
                     indent=2, default=repr))
    sys.exit(0 if (verdict in ("R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED",
                               ARCH_PASS.get(args.arch or "", ""))) else 1)


if __name__ == "__main__":
    main()
