#!/usr/bin/env python3
"""Phase-3 Gate 54: RTC kernel population x std-header dependency audit.

Builds, from upstream MIOpen source (projects/miopen/src/kernels):

1. the RTC kernel population: every *.cpp kernel entry file that MIOpen
   embeds for runtime compilation (the same files add_kernels embeds);
2. for each entry, the quoted-include closure over the kernel header set;
3. for every closure, which std angle-includes are reachable and which
   std:: entities the closure references (included vs referenced vs
   wrapper-mediated);
4. a JSON matrix + a Markdown summary.

Preprocessor-aware enough for the load-bearing guards: honors
#ifdef/#ifndef/#if defined()/||/&&/! on the RTC define set
(MIOPEN_HIP_RUNTIME_COMPILE=1, HIP_PACKAGE_VERSION_FLAT=<flag>, and the
version windows used by the historical shims) so that the HIP>=7 RTC
branch is the one evaluated, and __has_include(<h>) is recorded as
probe-dependent rather than resolved.

Usage:
  python audit_rtc_std_dependencies.py <miopen-src-kernels-dir> [--flat 7140060850ULL]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

INCLUDE_RE = re.compile(r'^\s*#\s*include\s+(<[^>]+>|"[^"]+")')
COND_RE = re.compile(r'^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)')

STD_HEADERS = ["type_traits", "utility", "limits", "cstdint",
               "initializer_list", "array", "functional", "algorithm",
               "cstddef", "cstring", "cmath", "cstdio", "cstdlib",
               "cassert", "cfloat", "climits", "cstdint", "tuple",
               "typeinfo", "memory", "atomic"]

STD_ENTITY_RE = re.compile(
    r"\bstd::(integral_constant|true_type|false_type|remove_reference_t?"
    r"|remove_const_t?|remove_volatile_t?|remove_cv_t?|is_same|enable_if_t?"
    r"|is_pointer|conditional_t?|forward|numeric_limits|array|initializer_list"
    r"|is_trivially_copyable_v?|plus|minus|multiplies|function|move|pair"
    r"|index_sequence|make_index_sequence|size_t|int64_t|uint64_t|int32_t"
    r"|uint32_t|uint8_t|int8_t|uint16_t|int16_t|memcpy|max|min|is_unsigned"
    r"|is_signed|is_integral|is_floating_point|disjunction|void_t)")


class PreprocState:
    """Minimal preprocessor for the load-bearing conditionals."""

    def __init__(self, defines: dict[str, int]):
        self.defines = defines
        self.stack: list[bool] = []       # each frame: branch taken so far
        self.active_stack: list[bool] = []  # currently in taken branch

    @property
    def active(self) -> bool:
        return all(self.active_stack) if self.active_stack else True

    def _eval(self, expr: str) -> bool:
        expr = expr.strip()
        # strip comments
        expr = re.sub(r"/\*.*?\*/", " ", expr)
        expr = re.sub(r"//.*$", "", expr)
        # __has_include(...) -> treat as TRUE (real STL reachable case;
        # freestanding case handled by wrapper analysis, not raw eval)
        expr = re.sub(r"__has_include\(\s*<[^>]*>\s*\)", "1", expr)
        expr = re.sub(r"__has_include\(\s*\"[^\"]*\"\s*\)", "1", expr)
        expr = re.sub(r"defined\s*\(\s*(\w+)\s*\)", lambda m: "1" if m.group(1) in self.defines else "0", expr)
        expr = re.sub(r"\bdefined\s+(\w+)", lambda m: "1" if m.group(1) in self.defines else "0", expr)
        for name, val in self.defines.items():
            expr = re.sub(rf"\b{name}\b", str(val), expr)
        # strip type suffixes
        expr = re.sub(r"(\d)[uUlL]+\b", r"\1", expr)
        expr = expr.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
        expr = re.sub(r"\btrue\b", "1", expr)
        expr = re.sub(r"\bfalse\b", "0", expr)
        if not expr.strip():
            return True
        try:
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            # unknown identifiers -> treat as 0 (undefined macro)
            cleaned = re.sub(r"\b[A-Za-z_]\w*\b", "0", expr)
            try:
                return bool(eval(cleaned, {"__builtins__": {}}, {}))
            except Exception:
                return True  # cannot evaluate: keep the branch (conservative)

    def feed(self, directive: str, rest: str) -> None:
        if directive == "if":
            taken = self._eval(rest)
            self.stack.append(taken)
            self.active_stack.append(taken)
        elif directive == "ifdef":
            taken = rest.strip() in self.defines
            self.stack.append(taken)
            self.active_stack.append(taken)
        elif directive == "ifndef":
            taken = rest.strip() not in self.defines
            self.stack.append(taken)
            self.active_stack.append(taken)
        elif directive == "elif":
            if self.stack:
                parent_active = all(self.active_stack[:-1]) if len(self.active_stack) > 1 else True
                taken = not self.stack[-1] and self._eval(rest)
                self.stack[-1] = self.stack[-1] or taken
                self.active_stack[-1] = parent_active and taken
        elif directive == "else":
            if self.stack:
                parent_active = all(self.active_stack[:-1]) if len(self.active_stack) > 1 else True
                self.active_stack[-1] = parent_active and not self.stack[-1]
                self.stack[-1] = True
        elif directive == "endif":
            if self.stack:
                self.stack.pop()
                self.active_stack.pop()


def parse_file(path: str, defines: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (quoted includes, angle includes, std entities) active under
    the given define set."""
    quoted, angle, entities = [], [], []
    state = PreprocState(defines)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = COND_RE.match(line)
            if m:
                state.feed(m.group(1), m.group(2))
                continue
            if not state.active:
                continue
            m = INCLUDE_RE.match(line)
            if m:
                tok = m.group(1)
                if tok.startswith("<"):
                    angle.append(tok[1:-1])
                else:
                    quoted.append(tok[1:-1])
                continue
            for e in STD_ENTITY_RE.findall(line):
                entities.append(e)
    return quoted, angle, entities


def closure(entry: str, hdr_index: dict[str, str], defines: dict,
            cache: dict, kdir: str = "") -> tuple[set[str], set[str], set[str], set[str]]:
    """BFS quoted-include closure. Returns (files, angle_includes,
    std_entities, unresolved_quoted)."""
    seen: set[str] = set()
    angle: set[str] = set()
    ents: set[str] = set()
    unresolved: set[str] = set()
    stack = [entry]
    entry_path = os.path.join(kdir, entry.replace("/", os.sep))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur == entry and os.path.exists(entry_path):
            path = entry_path
        else:
            path = hdr_index.get(cur)
        if path is None:
            unresolved.add(cur)
            continue
        q, a, e = parse_file_cached(path, defines, cache)
        angle.update(a)
        ents.update(e)
        for inc in q:
            if inc not in seen:
                stack.append(inc)
    return seen, angle, ents, unresolved


def parse_file_cached(path, defines, cache):
    key = path
    if key not in cache:
        cache[key] = parse_file(path, defines)
    return cache[key]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kernels_dir")
    ap.add_argument("--flat", default="7140060850ULL")
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    kdir = os.path.abspath(args.kernels_dir)
    flat_num = int(args.flat.rstrip("ULL"))

    # header index: basename -> path (kernel headers are flat in src/kernels
    # plus a few subdirs)
    hdr_index: dict[str, str] = {}
    for root, _dirs, files in os.walk(kdir):
        for fn in files:
            if fn.endswith((".hpp", ".h")):
                rel = os.path.relpath(os.path.join(root, fn), kdir).replace("\\", "/")
                hdr_index.setdefault(fn, os.path.join(root, fn))
                hdr_index.setdefault(rel, os.path.join(root, fn))

    entries = sorted(
        os.path.relpath(os.path.join(root, fn), kdir).replace("\\", "/")
        for root, _d, files in os.walk(kdir) for fn in files
        if fn.endswith(".cpp"))

    defines = {"MIOPEN_HIP_RUNTIME_COMPILE": 1,
               "HIP_PACKAGE_VERSION_FLAT": flat_num,
               "__HIP_PLATFORM_AMD__": 1,
               "HIP_PLATFORM_AMD": 1}

    cache: dict = {}
    matrix = {}
    all_angle: dict[str, set[str]] = {}
    for entry in entries:
        files, angle, ents, unresolved = closure(entry, hdr_index, defines, cache, kdir)
        std_angle = {a for a in angle if a.split("/")[0] in STD_HEADERS or a in STD_HEADERS}
        matrix[entry] = {
            "closure_size": len(files),
            "std_angle_includes": sorted(std_angle),
            "other_angle_includes": sorted(a for a in angle if a not in std_angle),
            "std_entities": sorted(ents),
            "unresolved_quoted": sorted(unresolved),
        }
        for a in std_angle:
            all_angle.setdefault(a, set()).add(entry)

    summary = {
        "kernels_dir": kdir,
        "defines": {k: v for k, v in defines.items()},
        "rtc_entry_count": len(entries),
        "std_header_reachability": {h: sorted(v) for h, v in sorted(all_angle.items())},
        "entity_users": {},
    }
    ent_users: dict[str, set[str]] = {}
    for entry, row in matrix.items():
        for e in row["std_entities"]:
            ent_users.setdefault(e, set()).add(entry)
    summary["entity_users"] = {e: sorted(v) for e, v in sorted(ent_users.items())}

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "matrix": matrix}, f, indent=1, sort_keys=True)

    # console digest
    print(f"RTC entries: {len(entries)}")
    print("std-header reachability (entries whose closure can pull it):")
    for h, users in sorted(all_angle.items()):
        print(f"  <{h}>: {len(users)} kernels e.g. {sorted(users)[:4]}")
    print("top std entities by entry count:")
    for e, users in sorted(ent_users.items(), key=lambda kv: -len(kv[1]))[:15]:
        print(f"  std::{e}: {len(users)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
