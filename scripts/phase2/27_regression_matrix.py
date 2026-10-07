"""Gate 33 reproduction: run the Phase-1 8-case BN A/B matrix (cases A-H)
in the current environment. NOTE: run from a scratch cwd — the Phase-1
script writes results to a cwd-relative path and must not touch the
Phase-1 evidence tree."""
import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "..", "03_batchnorm_matrix.py")
r = subprocess.run([sys.executable, os.path.abspath(script)])
sys.exit(r.returncode)
