# PHASE 1 — Third-round comment → change mapping

All comments by `averinevg`, review #5537906287, on f0f330c4. "Develop" = b8cf0e7b (merge base).

| # | Comment URL | Required change | File | Code change | Verification |
|---|---|---|---|---|---|
| 1 | r4286683533 | Drop comment above unchanged HIP-include block | `radix.hpp` | Delete 2-line `// Offline compilation needs these…` comment (lines 35–36); include block untouched | diff shows only comment lines removed; kthvalue 27/27 |
| 2 | r4286709599 | Drop partial-STL `#error` checks (type_traits + utility) | `miopen_type_traits.hpp`, `miopen_utility.hpp` | Delete `#if __has_include(<utility>)…#error…#endif` (type_traits 38–41) and `#if __has_include(<type_traits>)…#error…#endif` (utility 36–39). Selection `#if defined(MIOPEN_HIP_RUNTIME_COMPILE) && !__has_include(<X>)` untouched. Clang guard `#error` in miopen_initializer_list.hpp:17–19 KEPT (different, ABI purpose, not targeted) | no-STL gtest PASS; negative control still EXPECTED_FAIL with exact signature |
| 3 | r4286753510 | Shorten header comments to 1–2 lines | type_traits, utility, initializer_list | type_traits 28–35 → `// Minimal <type_traits> definitions for runtime compilation without a host C++ standard library.` · utility 28–33 → `// Minimal std::forward for runtime compilation without a host C++ standard library.` (reviewer's own example) · initializer_list 6–13 → 2 lines keeping the ABI constraint | visual + pre-commit pass |
| 4 | r4286772017 | Add blank line | `miopen_type_traits.hpp` (anchor line 107 = remove_cv_t) | Restore develop-style blank line between `remove_cv` struct and following definition (region restructured by comment 5 anyway; develop spacing restored throughout fallback) | diff vs develop shows blank-line parity |
| 5 | r4286919855 | Keep develop's definitions in place; drop obsolete HIP 6.x `#if` | `miopen_type_traits.hpp` | Move `integral_constant`/`true_type`/`false_type` from top of namespace to develop's position: after `remove_cv`, before `is_same` (develop text verbatim; no `#if` wrapper — already dropped in R2). Declaration-before-use holds: only `is_same`, `is_pointer_helper`, `is_trivially_copyable` derive from them, all later | host-STL compile + no-STL gtest (incl. `integral_constant<int,5>` selftest) PASS |
| 6 | r4286957313 | Don't modernize `typedef`; keep PR focused | `miopen_type_traits.hpp` | Restore develop spelling: `remove_reference`×3, `remove_const`×2, `remove_volatile`×2 → `typedef T type;`; `remove_cv` → `typedef typename remove_volatile<…>::type type;`. Also revert nonessential rewrites: `detail::` wrapper off `is_pointer_helper` (develop: flat in std), `is_pointer` uses develop text; `conditional` back to develop fwd-decl + two partial specializations (`predicate`/`X`/`Y` params); `conditional_t` back to develop spelling. New-in-PR items stay: `remove_const_t`/`remove_volatile_t`/`remove_cv_t` aliases, real `enable_if`/`enable_if_t` (replaces dropped `__hip_internal`), `is_trivially_copyable`(+`_v`), self-tests | consumer enumeration (batchnorm/RNN/kthvalue/fp8/configuration/tensor_view include these headers; no external `detail::` users) + full functional suite |
| 7 | r4287009694 | clang-format std::forward (lvalue overload) | `miopen_utility.hpp` | Revert one-line bodies to develop's multi-line form — this is also what CI clang-format emitted | local pre-commit/clang-format clean; CI pre-commit green on push |
| 8 | r4287010768 | clang-format std::forward (rvalue overload) | `miopen_utility.hpp` | Same as #7 (second overload) | Same as #7 |
| — (existing) | r4257536410 (round 2, outdated) | radix IWYU | `radix.hpp` | None — answered in c6ed8131 (unconditional `miopen_cstdint.hpp` + `miopen_type_traits.hpp`); reviewer summary accepts round 2 | thread state rechecked after push |

## Non-goals (explicitly out of scope)

- No rebase onto develop (c7943b12): PR mergeable, no conflict, no policy requirement, not requested.
- No changes to `tensor_view.hpp`, `CMakeLists.txt`, `hiprtc_selfcontained.cpp` (no comment targets them; test file frozen per mission).
- No removal of the Clang `#error` ABI guard in `miopen_initializer_list.hpp`.
- No removal of gtest negative controls.
- No new files, no CI-workflow edits.

**Gate A+D: PASS** — all 8 comments + 1 legacy thread accounted for.
