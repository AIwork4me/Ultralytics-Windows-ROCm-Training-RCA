# Patch Integrity Report — Phase 5.2 (Gates B01/B03/B10)

Source of record: pinned RCA checkout `repos/rca-evidence` @
`494907699f3b57095663f0a70b42278001a8efb7` (remote identity confirmed via
git transport AND GitHub API; local clone of `linux-w7900/preflight-readiness`
branch untouched).

## Canonical patch identities (recomputed twice independently: primary agent + audit subagent)

| # | Patch | Bytes | SHA256 |
|---|---|---|---|
| 1 | `0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch` | 15546 | `14719b8b4ae7b4370afa42249b56c130d7d42b9447701e57a702570eb12ed7e2` |
| 2 | `0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch` | 7444 | `7d40c314dcac87085178ba9d0c84bb2eced8f33ba8e9bd3a6151903d6ee4751e` |
| 3 | `0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch` | 27631 | `3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4` |

* Series SHA256 (`sha256_file_concat_v1`: raw LF bytes concatenated in
  order, no separator): `797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d`
* No CRLF in any patch; manifest-declared values == recomputed values.
* Support file `patches/phase5_1/canonical/README.md` (1809 B, sha256
  `10f7c7ccab19995217320032efe062517c36237dc5f4a85bf81e29f30e491ec1`)
  allowed by the directory audit and NOT part of the series hash.
* Manifest itself: 9471 B, sha256
  `58a6f9ce8afe2f41e80db8593c8711813b30c6418dfe0a5348dd6131d3bbafd8`
  (pinned by the consumer).

## Adversarial matrix outcome (22 attacks + 10 auditor attacks)

All negative attacks failed for their INTENDED reason — byte flips
(sha mismatch), order reversal/duplication (contiguity/series), injected
`0004-malicious.patch` (unexpected-file), symlink substitution (symlink
rejection), `../` and absolute paths (traversal/absolute), series/base/tree/
candidate tampering (pin mismatch), wrong evidence commit (HEAD mismatch),
missing patch, empty git object store (fail closed), `--apply` without
`ENABLE_APPLY=1` (REFUSED, exit 2). Controls (valid manifest; legitimate
README) PASS. Frozen checkout byte-identical after every run (verified, not
asserted).
