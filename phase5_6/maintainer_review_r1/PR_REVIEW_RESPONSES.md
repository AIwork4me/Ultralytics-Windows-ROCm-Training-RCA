# PR_REVIEW_RESPONSES — posted 2026-10-12 (all under review 5489844163)

1. Thread r4247502213 (use existing gtest infrastructure) — reply
   r4249478482: design summary (AddKernel production path, embedded
   BatchNorm kernel, -nostdinc isolation, paired-polarity probes,
   per-run cache-defeating nonce), Windows results (patched PASS;
   unpatched 54b079ca FAILS with 'type_traits' file-not-found single
   error; with-STL control passes on both legs), Linux honest-skip
   semantics, GPU-required trade vs the standalone, commit refs
   1d2481cf / 1845028f.

2. Thread r4247312895 (private-evidence-repo comments) — reply
   r4249487303: addressed in 1845028f; constraint reworded to the ABI
   rationale.

3. Thread r4247430203 (radix.hpp <limits> + guard merge) — reply
   r4249487738: addressed in 1845028f; MIOpenKthvalue.cpp recompiled in
   both ambient and STL-isolated quadrants through the production path.

Threads are intentionally left for the maintainer to resolve; nothing was
marked resolved from our side.
