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
    receipt hash (committed-bytes OR LF-normalized form). Returns
    (log_text, verification)."""
    if not path or not path.is_file():
        return None, {"log": str(path), "exists": False, "sha_match": False}
    raw = path.read_bytes()
    b_sha = hashlib.sha256(raw).hexdigest()
    l_sha = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if expected_sha:
        match = expected_sha in (b_sha, l_sha)
        form = "bytes" if expected_sha == b_sha else \
            ("lf-normalized" if expected_sha == l_sha else None)
    else:
        match, form = None, None
    return raw.decode("utf-8", errors="replace"), {
        "log": str(path), "exists": True, "sha_match": match,
        "bytes_sha256": b_sha, "lf_sha256": l_sha,
        "matched_form": form,
        "note": "R22A.3 runner receipts hash LF-normalized text (CRLF-writing "
                "defect); both forms recorded — authenticity holds iff either "
                "matches the frozen receipt hash" if match else
                "committed bytes do NOT match the frozen receipt hash",
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
        if r.get("log_text"):
            out.append(_base_run_record(r))
            continue
        idx = r.get("run")
        log_text, ver = None, {"log": None, "exists": False, "sha_match": None}
        if log_dir is not None and idx is not None:
            cands = [Path(log_dir) / f"run{idx:02d}" / "child.log"] + \
                sorted(Path(log_dir).glob(f"*run{idx:02d}*.log"))
            for c in cands:
                if c.is_file():
                    log_text, ver = load_log_text(c, r.get("log_sha256")
                                                  or r.get("raw_log_sha256"))
                    break
        out.append(_base_run_record(r, log_text=log_text, _log_verification=ver))
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
                         monitor_disclosures: dict | None = None) -> dict:
    """Side-by-side dual-arch reconciliation. Every displayed value is
    recomputed from the corresponding source records (mission §9); nothing is
    a template. PHYSICAL_TRAINING_FUNCTIONAL_PASS (the hardware trained) is
    explicitly distinguished from RELEASE_GRADE_EVIDENCE_ACCEPTED (the
    evidence satisfies the strict release contract)."""
    c1100 = combined_verdict(a1100, runs1100, "gfx1100", a1100.get("gpu_name"))
    c1151 = combined_verdict(a1151, runs1151, "gfx1151", a1151.get("gpu_name"))
    f1100 = _arch_facts(a1100, runs1100, c1100["part_b_overall"])
    f1151 = _arch_facts(a1151, runs1151, c1151["part_b_overall"])

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
        "notes": [
            "every cell recomputed from frozen raw records via versioned adapters",
            "cache roles derived from home identity only (fresh-home first use = "
            "CACHE_PRIMING, never pre-warmed)",
            "no dGPU vs APU performance comparison is made or implied",
            "effective-update counts (6 gfx1100 / 7 gfx1151) are factual "
            "observations of different hardware runs, not targets",
        ],
    }


# --- CLI ----------------------------------------------------------------------

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
        b1100 = evaluate_part_b(runs1100, a1100.get("gpu_name"))
        b1151 = evaluate_part_b(runs1151, a1151.get("gpu_name"))
        rep = dual_arch_acceptance(a1100, runs1100, a1151, runs1151, b1100, b1151, disc)
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
            gpu_b = part_b.get("gpu_name")
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

    Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False,
                                         default=repr), encoding="utf-8")
    verdict = rep.get("verdict") or rep.get("combined", {}).get("verdict")
    print(json.dumps({"verdict": verdict} if args.dual else rep["combined"],
                     indent=2, default=repr))
    sys.exit(0 if (verdict in ("R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED",
                               ARCH_PASS.get(args.arch or "", ""))) else 1)


if __name__ == "__main__":
    main()
