# P5.1-CANDIDATE-R2 canonical patch series

Upstream base: 7c5866144ac4b879be442563e2b49fa1c142ea36 (ROCm/rocm-libraries develop)
Order: 0001 → 0002 → 0003 (git am). Acceptance: `git write-tree` after am ==
b983caddf9f9f561e7d1b590deadb16267c2de15.

| # | commit | sha256 |
|---|--------|--------|
| 0001 | 01a77dab8c4cf23d1e49273fa3c88bb0bb4fc887 | 816946b4c8f52dbe044b62ae47b65c346989337eb63557f7bd1b829a1e71a76c |
| 0002 | 8188b803b8304fc5933caa52ee27a58d01a78b04 | 46044d8c9511fe3575ce8709623b18c627cc25bd076cb3cf231dc00c6ef1f460 |
| 0003 | f18c4de94b229bbe3e8501d70e3e2461425c69de | df7c3c3a3386732931b85d682c0d58638f7b4b48e169cede1cae254642d67f7e |

Series hash (sha256_file_concat_v1: SHA256 of the three files' LF bytes
concatenated in order, no separator):
48308f6dccfd80f099a458ad5033f815d95f86d2ab54dba1a0344c976b5a3f02

Verify: `python scripts/phase5_1_r2/verify_patch_identity.py <ref>` (25 checks).
Hash git blob bytes, never smudged working-tree copies (`*.patch -text` here).
Supersedes R1 (patches/phase5_1/canonical on branch phase5.1/windows-final-candidate-freeze
@ 4949076, series 797a69b5…) — R1 remains immutable for audit.
