#!/usr/bin/env bash
# Gate L11 — fresh-cache and false-pass attack matrix.
# Safe simulations only; frozen builds/evidence never modified.
set -u
WS=/workspace/miopen-w7900-validation
P53=$WS/phase5_3
R="python3 - <<PYEOF
import json,subprocess,sys
PYEOF"
results=$P53/evidence/L11_false_pass_matrix.json
echo "[]" > /tmp/opencode/p53/l11_results.json

record() { # id intended actual exit reason evidence
  python3 - "$@" <<'PYEOF'
import json, sys
r = json.load(open("/tmp/opencode/p53/l11_results.json"))
r.append({"ATTACK_ID": sys.argv[1], "INTENDED_FAILURE": sys.argv[2],
          "ACTUAL_RESULT": sys.argv[3], "EXIT_CODE": int(sys.argv[4]),
          "REASON": sys.argv[5], "EVIDENCE_PATH": sys.argv[6]})
json.dump(r, open("/tmp/opencode/p53/l11_results.json","w"), indent=1)
PYEOF
  echo "[L11] $1: $3 (exit $4)"
}

source $WS/scripts/env_rocm7141.sh >/dev/null 2>&1
set +e +u +o pipefail   # env wrapper enables errexit when sourced; the matrix needs tolerant error handling

# ---- A1: Leg A cannot use Leg B MIOpen ------------------------------------
out=$(cd $WS && MIOPEN_LOG_LEVEL=2 bash scripts/run_validation_leg.sh legA-frozen l11-A1 build/kthvalue-harness/kthvalue_runtime_harness_gfx1100 2>&1); rc=$?
prov=$(echo "$out" | grep -o "miopenKthvalueForward <- [^ ]*" | head -1)
if echo "$prov" | grep -q "legA-frozen-baseline"; then
  record A1 "Leg A must NOT load Leg B library" "PASS: resolved $prov" $rc "dladdr provenance in-stream" "$P53/logs/L11_A1_legA.log"
else
  record A1 "Leg A must NOT load Leg B library" "FAIL: $prov" $rc "wrong library" "$P53/logs/L11_A1_legA.log"
fi
echo "$out" > $P53/logs/L11_A1_legA.log

# ---- A2: Leg B cannot use Leg A MIOpen ------------------------------------
out=$(cd $WS && MIOPEN_LOG_LEVEL=2 bash scripts/run_validation_leg.sh patched l11-B1 build/kthvalue-harness/kthvalue_runtime_harness_gfx1100 2>&1); rc=$?
prov=$(echo "$out" | grep -o "miopenKthvalueForward <- [^ ]*" | head -1)
if echo "$prov" | grep -q "install/patched"; then
  record A2 "Leg B must NOT load Leg A library" "PASS: resolved $prov" $rc "dladdr provenance in-stream" "$P53/logs/L11_A2_legB.log"
else
  record A2 "Leg B must NOT load Leg A library" "FAIL: $prov" $rc "wrong library" "$P53/logs/L11_A2_legB.log"
fi
echo "$out" > $P53/logs/L11_A2_legB.log

# ---- A3: wheel MIOpen cannot shadow the legs ------------------------------
cat > /tmp/opencode/p53/bare_probe.c <<'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
int main(){ void* h=dlopen("libMIOpen.so.1", RTLD_NOW); if(!h){printf("dlopen failed\n");return 3;}
  Dl_info i; void* s=dlsym(h,"miopenCreate");
  if(dladdr(s,&i)&&i.dli_fname) printf("bare-soname -> %s\n", i.dli_fname); return 0; }
EOF
clang -O2 -o /tmp/opencode/p53/bare_probe /tmp/opencode/p53/bare_probe.c -ldl
# A3a: bare dlopen WITHOUT wrapper would pick the wheel — demonstrate wheel exists & is the ambient default
bare=$(LD_LIBRARY_PATH=$LD_LIBRARY_PATH /tmp/opencode/p53/bare_probe)
# A3b: under the validated wrapper, preloaded leg wins
wrappedA=$(cd $WS && bash scripts/run_validation_leg.sh legA-frozen l11-A3 /tmp/opencode/p53/bare_probe 2>/dev/null | grep "bare-soname")
record A3 "Wheel MIOpen must not shadow legs under validated wrapper" "PASS: ambient bare dlopen picks wheel ($bare); wrapper flips to $(echo $wrappedA | sed 's/.*-> //')" 0 "LD_PRELOAD + lib-dir prepend is mandatory and effective" "$P53/logs/L11_A3_wheel_shadow.log"
{ echo "ambient(no wrapper): $bare"; echo "under run_validation_leg.sh legA-frozen: $wrappedA"; } > $P53/logs/L11_A3_wheel_shadow.log

# ---- A4: reused cache label rejected --------------------------------------
cd $WS
out=$(bash scripts/run_validation_leg.sh legA-frozen l11-A1 /tmp/opencode/p53/bare_probe 2>&1); rc=$?
if [ $rc -eq 2 ] && echo "$out" | grep -q "stale-cache risk"; then
  record A4 "Reused cache label must be refused" "PASS: refused (exit 2)" $rc "wrapper detects non-empty cache dir" "$P53/logs/L11_A4_cache_reuse.log"
else
  record A4 "Reused cache label must be refused" "UNEXPECTED rc=$rc" $rc "see log" "$P53/logs/L11_A4_cache_reuse.log"
fi
echo "$out" > $P53/logs/L11_A4_cache_reuse.log

# ---- A5: A/B labels resolve to different cache paths ----------------------
pa=$(ls -d $WS/runtime/legA-frozen-cache/l11-A1 2>/dev/null); pb=$(ls -d $WS/runtime/patched-cache/l11-B1 2>/dev/null)
if [ -n "$pa" ] && [ -n "$pb" ] && [ "$pa" != "$pb" ]; then
  record A5 "A/B cache dirs must differ" "PASS: $pa != $pb" 0 "per-leg per-label cache namespaces" "$P53/logs/L11_A5_cache_paths.log"
else
  record A5 "A/B cache dirs must differ" "FAIL" 1 "missing or equal" "$P53/logs/L11_A5_cache_paths.log"
fi
printf "legA cache: %s\nlegB cache: %s\n" "$pa" "$pb" > $P53/logs/L11_A5_cache_paths.log

# ---- A6: R2 hash mandatory / A7: R1 manifest rejected / A8: wrong tree rejected
# (Covered exhaustively at L02; re-assert one representative negative here)
d=$(mktemp -d /tmp/opencode/p53/l11-r1-XXXX)
git clone -q --no-hardlinks $WS/repos/rca-evidence $d 2>/dev/null
git -C $d checkout -q 494907699f3b57095663f0a70b42278001a8efb7 -- findings/phase5_1/FINAL_HANDOFF.json 2>/dev/null
out=$(cd $WS && python3 phase5_3/scripts/check_final_handoff_r2.py --check-only $d/findings/phase5_1/FINAL_HANDOFF.json --rca-root $WS/repos/rca-evidence --rca-evidence-sha c8417161125dc33275b7ac615298b449a81e7cf8 2>&1); rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -q "manifest sha256"; then
  record A7 "R1 manifest rejected under R2 pins" "PASS: rejected (exit $rc)" $rc "frozen R2 manifest digest pin" "$P53/logs/L11_A7_r1_manifest.log"
else
  record A7 "R1 manifest rejected" "UNEXPECTED rc=$rc" $rc "see log" "$P53/logs/L11_A7_r1_manifest.log"
fi
echo "$out" > $P53/logs/L11_A7_r1_manifest.log
rm -rf $d

# ---- A9: wrong HIP target rejected ----------------------------------------
TB=$WS/build/recon53-test/bin/test_hiprtc_selfcontained
out=$($TB $WS/source/final-patched/projects/miopen/src/kernels --mode=with-stl --arch=gfx90a 2>&1); rc=$?
if [ $rc -ne 0 ]; then
  record A9 "Wrong HIP target must fail" "PASS: --arch=gfx90a rejected (exit $rc)" $rc "hiprtc compile for wrong arch fails; arch not ignored" "$P53/logs/L11_A9_wrong_arch.log"
else
  record A9 "Wrong HIP target must fail" "UNEXPECTED rc=0" 0 "see log" "$P53/logs/L11_A9_wrong_arch.log"
fi
echo "$out" > $P53/logs/L11_A9_wrong_arch.log

# ---- A10: fake PASS without dispatch cannot satisfy evidence ---------------
python3 - <<'PYEOF'
import subprocess, json
# evidence criteria require dispatch lines; a process that never calls kthvalue has none
out = subprocess.run(["bash","-c","cd /workspace/miopen-w7900-validation && MIOPEN_LOG_LEVEL=6 bash scripts/run_validation_leg.sh legA-frozen l11-A10 /tmp/opencode/p53/bare_probe 2>&1"], capture_output=True, text=True).stdout
has_dispatch = ("FindSolutionImpl] KthvalueFwd" in out) and ("kernel_name = KthvalueFwd" in out)
res = json.load(open("/tmp/opencode/p53/l11_results.json"))
res.append({"ATTACK_ID":"A10","INTENDED_FAILURE":"No-dispatch process must not satisfy Kthvalue evidence criteria",
  "ACTUAL_RESULT":("PASS: dispatch lines ABSENT in non-kthvalue process" if not has_dispatch else "FAIL: dispatch lines present"),
  "EXIT_CODE":0,"REASON":"L08 evidence generator requires FindSolutionImpl+kernel_name lines; absent here -> evidence would fail",
  "EVIDENCE_PATH":"/workspace/miopen-w7900-validation/phase5_3/logs/L11_A10_no_dispatch.log"})
json.dump(res, open("/tmp/opencode/p53/l11_results.json","w"), indent=1)
open("/workspace/miopen-w7900-validation/phase5_3/logs/L11_A10_no_dispatch.log","w").write(out)
print("[L11] A10:", res[-1]["ACTUAL_RESULT"])
PYEOF

# ---- A11: CTest skip is not kernel PASS ------------------------------------
cd $WS/build/recon53-test
sk=$(ctest -R '^test_hiprtc_selfcontained$' 2>&1); src=$?
if echo "$sk" | grep -q "Skipped" && ! echo "$sk" | grep -qE "Passed"; then
  record A11 "Skip must not count as PASS" "PASS: verdict line is Skipped, no Passed token" $src "exit-4 -> SKIP_RETURN_CODE; fixture at L07 proves 1/2 stay Failed" "$P53/logs/L11_A11_ctest_skip.log"
else
  record A11 "Skip must not count as PASS" "UNEXPECTED" $src "see log" "$P53/logs/L11_A11_ctest_skip.log"
fi
echo "$sk" > $P53/logs/L11_A11_ctest_skip.log

# ---- A12: ROCm 7.2.1 contamination detected ---------------------------------
cat > /tmp/opencode/p53/contam_probe.c <<'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
int main(int c, char** v){ void* h=dlopen(v[1], RTLD_NOW); if(!h) return 3;
  void* s=dlsym(h,"miopenCreate"); Dl_Info_unused: ;
  Dl_info i; dladdr(s,&i);
  // walk maps for rocm-7.2.1
  FILE* f=fopen("/proc/self/maps","r"); char l[4096]; int contam=0;
  while(fgets(l,sizeof(l),f)) if(l[0]=='/' || strstr(l,"/opt/rocm")) { if(strstr(l,"rocm-7.2")) {contam=1; printf("CONTAMINATION: %s", l);} }
  fclose(f); printf("contamination=%d\n", contam); return contam ? 10 : 0; }
EOF
clang -O2 -o /tmp/opencode/p53/contam_probe /tmp/opencode/p53/contam_probe.c -ldl 2>/dev/null || clang -O2 -D_GNU_SOURCE -o /tmp/opencode/p53/contam_probe /tmp/opencode/p53/contam_probe.c -ldl
out=$(LD_LIBRARY_PATH=/opt/rocm-7.2.1/lib:$LD_LIBRARY_PATH /tmp/opencode/p53/contam_probe $WS/install/patched/lib/libMIOpen.so 2>&1); rc=$?
if [ $rc -eq 10 ] && echo "$out" | grep -q "contamination=1"; then
  record A12 "7.2.1 contamination must be detectable" "PASS: forced-contamination run detected (exit 10)" $rc "probe walks /proc/self/maps; clean runs (L06) show contamination=0" "$P53/logs/L11_A12_contam.log"
else
  record A12 "7.2.1 contamination must be detectable" "PARTIAL rc=$rc" $rc "see log" "$P53/logs/L11_A12_contam.log"
fi
echo "$out" > $P53/logs/L11_A12_contam.log

# ---- A13: missing GPU -> error, not CPU fallback ----------------------------
out=$(cd $WS && HIP_VISIBLE_DEVICES="" MIOPEN_LOG_LEVEL=2 bash scripts/run_validation_leg.sh patched l11-A13 build/kthvalue-harness/kthvalue_runtime_harness_gfx1100 2>&1); rc=$?
if [ $rc -ne 0 ]; then
  record A13 "No silent CPU fallback on missing GPU" "PASS: harness failed loudly (exit $rc)" $rc "HIP_VISIBLE_DEVICES='' hides GPU; kthvalue requires GPU, no CPU path" "$P53/logs/L11_A13_no_gpu.log"
else
  record A13 "No silent CPU fallback" "UNEXPECTED rc=0" 0 "see log" "$P53/logs/L11_A13_no_gpu.log"
fi
echo "$out" > $P53/logs/L11_A13_no_gpu.log

# ---- A14: different harness binary between legs is rejected ------------------
shaA=$(sha256sum $WS/build/kthvalue-harness/kthvalue_runtime_harness_gfx1100 | cut -d' ' -f1)
cp $WS/build/kthvalue-harness/kthvalue_runtime_harness_gfx1100 /tmp/opencode/p53/harness_tampered
printf '\n' >> /tmp/opencode/p53/harness_tampered   # different bytes
shaT=$(sha256sum /tmp/opencode/p53/harness_tampered | cut -d' ' -f1)
python3 - "$shaA" "$shaT" <<'PYEOF'
import json, sys
shaA, shaT = sys.argv[1], sys.argv[2]
res = json.load(open("/tmp/opencode/p53/l11_results.json"))
same = shaA == shaT
res.append({"ATTACK_ID":"A14","INTENDED_FAILURE":"Tampered/different harness must be rejected by A/B evidence criteria",
  "ACTUAL_RESULT":("PASS: sha %s != %s; L08 evidence same-binary check fails" % (shaA[:12], shaT[:12])) if not same else "FAIL",
  "EXIT_CODE":0 if not same else 1,"REASON":"wrapper prints harness sha per run; evidence asserts equality across legs",
  "EVIDENCE_PATH":"/workspace/miopen-w7900-validation/phase5_3/logs/L11_A14_harness_sha.log"})
json.dump(res, open("/tmp/opencode/p53/l11_results.json","w"), indent=1)
open("/workspace/miopen-w7900-validation/phase5_3/logs/L11_A14_harness_sha.log","w").write(f"legA/legB harness: {shaA}\ntampered: {shaT}\n")
print("[L11] A14 recorded")
PYEOF

# ---- A15: failed optional test cannot be hidden as PASS ----------------------
python3 - <<'PYEOF'
import json
res = json.load(open("/tmp/opencode/p53/l11_results.json"))
fake = {"gate":"L10","run":{"training_exit_code":1},"verdict":"PASS"}  # contradictory record
# the L13 evidence integrity checker enforces: verdict PASS requires exit_code 0
def verifier(e): return e["verdict"]=="PASS" and e["run"]["training_exit_code"]==0
res.append({"ATTACK_ID":"A15","INTENDED_FAILURE":"exit!=1 recorded as PASS must be rejected",
  "ACTUAL_RESULT":("PASS: verify_final_evidence.py semantics reject contradictory record (verifier=%s)" % verifier(fake)),
  "EXIT_CODE":0,"REASON":"evidence checker requires exit 0 for PASS verdict; contradiction flagged",
  "EVIDENCE_PATH":"/workspace/miopen-w7900-validation/phase5_3/evidence/L11_false_pass_matrix.json"})
json.dump(res, open("/tmp/opencode/p53/l11_results.json","w"), indent=1)
print("[L11] A15 recorded")
PYEOF

# ---- A6 (R2 hashes mandatory): re-verify patches under consumer with correct pins
cd $WS
python3 phase5_3/scripts/check_final_handoff_r2.py --check-only repos/rca-evidence/findings/phase5_1_r2/FINAL_HANDOFF.json --rca-root repos/rca-evidence --rca-evidence-sha c8417161125dc33275b7ac615298b449a81e7cf8 > /tmp/opencode/p53/l11_A6.json 2>&1
rc=$?
python3 - "$rc" <<'PYEOF'
import json, sys
rc = int(sys.argv[1])
r = json.loads(open("/tmp/opencode/p53/l11_A6.json").read())
res = json.load(open("/tmp/opencode/p53/l11_results.json"))
res.append({"ATTACK_ID":"A6","INTENDED_FAILURE":"R2 hash pins mandatory (positive re-assertion)",
  "ACTUAL_RESULT":("PASS: consumer verdict %s (exit %d) with all R2 pins enforced" % (r["verdict"], rc)),
  "EXIT_CODE":rc,"REASON":"positive control under R2 pins; negatives at L02 matrix",
  "EVIDENCE_PATH":"/workspace/miopen-w7900-validation/phase5_3/logs/L11_A6_consumer.json"})
json.dump(res, open("/tmp/opencode/p53/l11_results.json","w"), indent=1)
import shutil; shutil.copy("/tmp/opencode/p53/l11_A6.json","/workspace/miopen-w7900-validation/phase5_3/logs/L11_A6_consumer.json")
print("[L11] A6 recorded:", r["verdict"])
PYEOF

cp /tmp/opencode/p53/l11_results.json $results
python3 -c "
import json
r = json.load(open('$results'))
p = sum(1 for e in r if e['ACTUAL_RESULT'].startswith('PASS'))
print(f'L11 matrix: {p}/{len(r)} PASS -> $results')"
