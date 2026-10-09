"""Phase 5.4 - provenance for the two ad-hoc CI checks that were executed
interactively during Gate P54-04/P54-05 (Reviewer B MINOR-1: make every
load-bearing log reproducible by a committed command).

Reproduces exactly what produced:
  logs/ci/ci_ctest_bare_env.log     (F-C2-4 revalidation: bare-env ctest)
  logs/ci/bf16_leg_ctest_n.log      (restricted-leg skip parity)

Usage: C:/Users/rocm/miniconda3/envs/yolo_amd/python.exe <this file>
Exits nonzero if either check deviates from the recorded verdicts.
"""
import subprocess
import sys
from pathlib import Path

CTEST = (Path(r"C:\Users\rocm\Desktop\YOLO_AMD\phase3_buildtools") /
         "Lib/site-packages/cmake/data/bin/ctest.exe")
CI_TEST = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\phase5_4_build\ci_test")
CI_BF16 = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\phase5_4_build\ci_test_bf16")
OUT = Path(__file__).resolve().parents[1] / "logs" / "ci"

# Deliberately minimal environment: NO ambient ROCm / MSVC / conda paths.
# The CMake-level WIN32 PATH prepend in the test's ENVIRONMENT property is
# then the only source of hiprtc DLL resolution (the thing being proven).
BARE_ENV = {"PATH": r"C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem",
            "SystemRoot": r"C:\Windows"}


def run(label, args, env, expect):
    p = subprocess.run([str(CTEST), *args], capture_output=True, text=True,
                       env=env)
    out = p.stdout + p.stderr
    (OUT / f"{label}.replay.log").write_text(
        out + f"\nrc={p.returncode}\n", encoding="utf-8")
    ok = expect(p.returncode, out)
    print(f"[{label}] rc={p.returncode} -> {'OK' if ok else 'UNEXPECTED'}")
    return ok


def main() -> int:
    ok = run(
        "ci_ctest_bare_env",
        ["-R", r"^test_hiprtc_selfcontained$", "--output-on-failure",
         "--test-dir", str(CI_TEST)],
        BARE_ENV,
        lambda rc, out: rc == 0 and "Passed" in out and "Skipped" not in out)
    ok &= run(
        "bf16_leg_ctest_n",
        ["-N", "-R", "hiprtc", "--test-dir", str(CI_BF16)],
        BARE_ENV,
        lambda rc, out: rc == 0 and "(Disabled)" in out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
