# P13.8 — 证据与声明审计

日期:2026-11-15 · 原则:历史 raw/快照不可改;活文档对齐当前证据;无数据删除

## 1. 565 vs 575 对账(定谳)

- **575 = 权威计数**(2026-11-15 实测 `verify_release_closure.py` → 575 checks / 0 violations / exit 0)。
- 565 = P9 wave-3 时点校准值;最终批次(P9 收尾)新增 10 检查后被遗留于部分文档。
- 处置:活文档已更正(Draft PR #13 body、GO_NO_GO P13 addendum);`P9_PR_BODY.md` 等带日期快照**保持原样**(历史不可改写);旧数值均标注来源时点。

## 2. 历史 P8 vs 当前 P9/P13 verdict

P8 的 "third environment" 限制已被 P9(G4 于 ENV A/B 重跑)消除;P13 维持。本文件不重写 P8_INDEPENDENT_AUDIT.md,差异由 GO_NO_GO addendum 链条承载。

## 3. P9→P13 表述修正(唯一一处 verdict 级降级,raw 不动)

| 原表述(P9) | 修正(P13.2) |
|---|---|
| "ENV B 混合态确定性崩溃 3/3;根因 = 混合 bin 目录 fdb 不可读 → 运行时编译产生坏 kernel 对象" | "P9 会话状态窗口内 3/3 崩溃(实机证据存档);P13 同 env/DLL/缓存 3 种独立配置不可复现;'fdb 不可读'=文件不存在(良性,官方 3.5.2 不发起该查找);真实根因 **UNRESOLVED**,三候选归档" |

依据:`P13_INVALID_KERNEL_FILE_RCA.md` + raw(`p132_minconv_*`、`p132_probe_*`、`p132_checkamp_real_*`、`p132_x1_*`、`p132_default_cache_state_before.json`)。

## 4. 上游状态对账(2026-11-15)

| 项 | 状态 |
|---|---|
| ultralytics #27198 | open @ `eca13ba`(P13.1 重建);Docs/CLA/14 项绿,torch1.8 兼容修复后 Tests 重跑中;**未合并** |
| rocm-libraries #13437 | merged(2026-10-19)— 不重提 |
| rocm-libraries #15862 | open,0 维护者评论;P13.3 切点证据评论已发 |
| rocm-libraries #15861 | open,0 维护者评论;P13.7 源码级分析+X1 计划评论已发 |
| Owner 授权 | CLA 由 Owner 本人签署(2026-11-14T23:47Z);上游合并不代行 |

## 5. 证据留存规则执行

- 本会话无删除任何历史证据;新增 raw 全部带 run-id + 环境指纹(见 P13_BASELINE_AND_ENVIRONMENT.md)。
- `p132_default_cache_state_before.json` 记录了唯一一次接触 default 缓存前的全量哈希快照(运行后 mtime 被刷新的事实如实记录于 P13.2 §5)。
- 已知缺口:P9 的 `checkamp84212_envB_logs/` 目录缺失(仅提交了 harness)— stderr 已在 JSON stderr_tail 内保全;补档待 P9 会话临时目录残留清点(不改历史)。

## 6. "第三环境"旧注记

P8 时代的 miniconda-base G4 运行(pre-fix 7.14.0)保留为历史;现行 verdict 全部基于 ENV A/B 双环境 + in-process DLL probe。无遗留未对齐的 PASS。
