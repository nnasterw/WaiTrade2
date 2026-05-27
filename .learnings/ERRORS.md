## [ERR-20260518-001] apply_patch_context

**Logged**: 2026-05-18T00:00:00+08:00
**Priority**: low
**Status**: pending
**Area**: tooling

### Summary
一次 `apply_patch` 因上下文行顺序与实际文件不一致而失败。

### Error
```
apply_patch verification failed: Failed to find expected lines in scripts/yaml_to_set.py
```

### Context
- 操作: 为 `scripts/yaml_to_set.py` 添加 v99g2 新参数映射。
- 原因: 补丁同时匹配两段上下文，但文件中的目标字段顺序与预想不同。

### Suggested Fix
以后对已有映射表做补丁时，先读取目标片段，再用更小上下文分段 patch。

### Metadata
- Reproducible: yes
- Related Files: scripts/yaml_to_set.py

---

## [ERR-20260526-003] yaml_anchor_missing_v11b_xau_r7

**Logged**: 2026-05-26T20:43:00+08:00
**Priority**: high
**Status**: fixed
**Area**: strategy-config

### Summary
新增 `v11xau_start_r7_nov_guard` 时继承 `*v11b_xau_r7_m1_monthguard`，但父策略未声明同名 anchor，导致 YAML smoke test 和 `.set` 生成失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11b_xau_r7_m1_monthguard'
```

### Context
- 操作: 为 2024-11 首月 `$200 -> $300+` 缺口设计 R7 低余额小时过滤候选。
- 修复: 将 `v11b_xau_r7_m1_monthguard:` 改为 `v11b_xau_r7_m1_monthguard: &v11b_xau_r7_m1_monthguard`。
- 这是同类 anchor 漏写的重复错误，应在新增继承前先补父节点 anchor。

### Suggested Fix
在 `config/strategies.yaml` 写 `<<: *parent` 前，先 `rg -n "^parent:" config/strategies.yaml` 检查父节点是否是 `parent: &parent`；没有 anchor 就先补，再跑 YAML smoke test。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: ERR-20260526-001, ERR-20260526-002
- Recurrence-Count: 5

---

## [ERR-20260527-001] parallel_mt5_backtest_cache_race

**Logged**: 2026-05-27T00:00:00+08:00
**Priority**: high
**Status**: fixed
**Area**: backtest

### Summary
同时启动多个 `scripts/mt5_cli_backtest.py --background` 进程会竞争同一个 MT5 `Tester/cache` 目录和 `backtest.ini`，导致回测失败或结果互相污染。

### Error
```
FileExistsError: [Errno 17] File exists: '.../MetaTrader 5/Tester/cache'
```

### Context
- 操作: 并行补跑 `v11_r53_j2_g30m10_no072223` 在 XAU 的 2026-01/02/03 月初窗口。
- 影响: 2026-02 回测失败；其余并行结果也需谨慎看待，因为共用 `backtest.ini` 和 terminal 日期。
- 修复: 立即停止并行方式，后续 MT5 Strategy Tester CLI 回测串行执行。

### Suggested Fix
MT5 CLI 回测只能串行跑；`multi_tool_use.parallel` 仅用于文件读取、`rg`、`sed`、`git diff` 等无共享写状态命令，不用于 MT5 回测。

### Metadata
- Reproducible: yes
- Related Files: scripts/mt5_cli_backtest.py
- Tags: mt5, backtest, concurrency

---

## [ERR-20260526-002] yaml_anchor_missing_v11xau_start

**Logged**: 2026-05-26T18:00:00+08:00
**Priority**: medium
**Status**: fixed
**Area**: strategy-config

### Summary
新增 `v11xau_start_*` 实验策略时，子策略继承 `*v11xau_start_risk10_pt50`，但父策略未声明 anchor，导致 YAML 解析和 preset 生成失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11xau_start_risk10_pt50'
```

### Context
- 操作: 校验 `python3 scripts/yaml_to_set.py v11xau_start_risk10_pt50`。
- 修复: 将父节点改为 `v11xau_start_risk10_pt50: &v11xau_start_risk10_pt50`。

### Suggested Fix
所有会被后续实验继承的策略，都必须在首次定义时同步加同名 YAML anchor。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: ERR-20260526-001
- Recurrence-Note: 同一批实验中 `v11xau_start_fix050_pt50` 继承 `*v11xau_start_fix030_pt50` 也触发同类问题，已同步给 `fix030` 加 anchor；后续 `v11xau_start_f050_h1415` 又继承 `*v11xau_start_fix050_pt50`，因此 `fix050` 也补为 anchor。

---

## [ERR-20260518-003] python_command_alias

**Logged**: 2026-05-18T17:00:00+08:00
**Priority**: low
**Status**: pending
**Area**: tooling

### Summary
本机环境没有 `python` 命令，只有 `python3`。

### Error
```
zsh:1: command not found: python
```

### Context
- 操作: 解析 MT5 Agent 日志时误用 `python - <<'PY'`。
- 环境: `/Users/wen/Projects/ClaudeCode/WaiTrade2`，zsh。

### Suggested Fix
本仓库命令统一使用 `python3`，尤其是回测、日志分析和小脚本。

### Metadata
- Reproducible: yes
- Related Files: scripts/

---

## [ERR-20260520-001] yaml_anchor_missing_after_strategy_append

**Logged**: 2026-05-20T17:12:00+08:00
**Priority**: medium
**Status**: fixed
**Area**: strategy-config

### Summary
新增策略配置后，后续实验用 `<<: *v11_r4_hour_weight` 继承，但源策略未声明 `&v11_r4_hour_weight` anchor，导致 YAML 解析失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11_r4_hour_weight'
```

### Context
- 操作: `python3 scripts/yaml_to_set.py --all --output-dir mql5/Presets`
- 影响: preset 生成和依赖 `config/strategies.yaml` 的 pytest 失败。

### Suggested Fix
新增可继承实验底座时，先写成 `strategy_name: &strategy_name`；运行 `python3 scripts/yaml_to_set.py --all` 作为 YAML anchor 烟测。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: 2026-05-20 Round9/Round10 再次发生同类问题，`v11_r9_profit_push` 继承 `*v11_r9_quality_core`、Round10 继承 `*v11_r9_quality_soft` 前未声明 anchor；2026-05-21 Round12 再次继承 `*v11_r10_qsoft_freq` / `*v11_r10_qsoft_6k` 前未声明 anchor；Round15 再次继承 `*v11_r11_qsoft_l45_add1120` 前未声明 anchor；Round16 再次继承 `*v11_r15_q1120_h1push` 前未声明 anchor；Round18 再次继承 `*v11_r18_shallow_h1320_r3` 前未声明 anchor；Round23 再次继承 `*v11j1` 前未声明 anchor；Round25 再次继承 `*v11_r23_j1_profit_r33_lg28` 和 `*v11_r25_j1_swp_l05` 前未声明 anchor；Round43 再次继承 `*v11_r42_j2_p038_m16_g10k` 前未声明 anchor；Round44 再次继承 `*v11_r43_j2_p038_m16_g20k` 前未声明 anchor；Round53 再次继承 `*v11_r53_j2_g30m10_no0722` 前未声明 anchor，已补齐。
- Recurrence-Count: 13

---

## [ERR-20260518-002] mt5_backtest_expert_path

**Logged**: 2026-05-18T00:00:00+08:00
**Priority**: high
**Status**: fixed
**Area**: backtest

### Summary
EA 已迁移到 `WaiTrade2`，但回测脚本默认 expert 仍指向旧 `WaiTrade`，导致第一次 v99g2 烟测跑了旧 EA。

### Error
```
Tester test Experts\WaiTrade\WaiTrade_OB.ex5 ...
```

### Context
- 操作: `python3 scripts/mt5_cli_backtest.py --strategies v99g1,v99g2,v99g3 --symbol XAUUSDm --days 30`
- 现象: 日志显示旧路径结果 52笔/$222.08；修正为 `WaiTrade2\WaiTrade_OB` 后变为新 EA 路径结果。

### Suggested Fix
EA 目录迁移时必须同步 `backtest_defaults.expert`、macOS/Windows 回测脚本默认值、live runner 和文档命令，并检查 Agent 日志中的 `test Experts\...\*.ex5` 行。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml, scripts/mt5_cli_backtest.py, scripts/mt5_backtest_win.py

---

## [ERR-20260521-001] yaml_anchor_missing_round27

**Logged**: 2026-05-21T16:15:00+08:00
**Priority**: medium
**Status**: fixed
**Area**: strategy-config

### Summary
Round27 新增 `v11j2` 派生策略后，继续用 `<<: *v11_r27_j2_hourq` 和 `<<: *v11_r27_j2_midpush` 继承，但源节点未声明 anchor，导致 YAML 解析失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11_r27_j2_hourq'
```

### Context
- 操作: `python3 scripts/mt5_cli_backtest.py --strategies v11_r27_j2_hourq,v11_r27_j2_guard_np2,v11_r27_j2_midpush,v11_r27_j2_midpush_np2 --symbol BTCUSDm --from 2025.11.22 --to 2026.05.21 --timeout 360`
- 原因: `v11_r27_j2_guard_np2` / `v11_r27_j2_midpush_np2` 依赖的父节点没有写成 `strategy: &strategy`。

### Suggested Fix
新增会被其他策略复用的候选节点时，定义当下就补上同名 anchor，并在批量回测前先跑一次 YAML smoke test（如 `python3 -c "import yaml; yaml.safe_load(open('config/strategies.yaml'))"`）。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: ERR-20260520-001

---

## [ERR-20260522-001] backtest_digest_report_arg

**Logged**: 2026-05-22T15:25:00+08:00
**Priority**: low
**Status**: fixed
**Area**: backtest

### Summary
调用 `scripts/backtest_digest.py` 时误把报告路径作为位置参数传入，但脚本接口要求显式使用 `--report`。

### Error
```
backtest_digest.py: error: the following arguments are required: --report
```

### Context
- 操作: 为 Round41 BTC 720天回测报告生成 digest。
- 影响: digest 生成失败一次，随后用 `python3 scripts/backtest_digest.py --report <report> --export-csv` 修正。

### Suggested Fix
分析 MT5 报告时统一使用 `python3 scripts/backtest_digest.py --report results/backtest/<file>.txt --export-csv`，不要依赖位置参数。

### Metadata
- Reproducible: yes
- Related Files: scripts/backtest_digest.py

---

## [ERR-20260526-001] yaml_anchor_missing_v11b_xau_r26

**Logged**: 2026-05-26T08:02:28Z
**Priority**: medium
**Status**: fixed
**Area**: strategy-config

### Summary
R28 继承 `*v11b_xau_r26_m1_reentry_target_ext2`，但 R26 未声明同名 anchor，导致 YAML 解析和 preset 生成失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11b_xau_r26_m1_reentry_target_ext2'
```

### Context
- 操作: 校验 `v11b_xau_r27_m1_pf2_hourcut` / `v11b_xau_r28_m1_pf2_hourcut_strict`。
- 修复: 将父节点改为 `v11b_xau_r26_m1_reentry_target_ext2: &v11b_xau_r26_m1_reentry_target_ext2`。

### Suggested Fix
新增可能被继承的策略版本时，先写成 `strategy_name: &strategy_name`，再追加子策略；批量回测前必须做 YAML smoke test。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: ERR-20260521-001
- Recurrence-Count: 3

---

## [ERR-20260526-004] yaml_anchor_missing_v11xau_start_fage_monthgate

**Logged**: 2026-05-26T19:58:00+08:00
**Priority**: high
**Status**: fixed
**Area**: strategy-config

### Summary
新增 `v11xau_start_fage_mg26_fix020` / `fix050` 时继承 `*v11xau_start_fage_2026_monthgate`，但父策略未声明 anchor，导致 MT5 回测脚本加载 YAML 失败。

### Error
```
yaml.composer.ComposerError: found undefined alias 'v11xau_start_fage_2026_monthgate'
```

### Context
- 操作: 回测 `v11xau_start_fage_mg26_fix020,v11xau_start_fage_mg26_fix050` 的 2026.04.01~2026.05.01 首月窗口。
- 原因: 重复违反“被子策略继承的父节点必须写成 `strategy: &strategy`”规则。
- 修复: 将 `v11xau_start_fage_2026_monthgate:` 改为 `v11xau_start_fage_2026_monthgate: &v11xau_start_fage_2026_monthgate`。

### Suggested Fix
每次在 `config/strategies.yaml` 增加 `<<: *新父策略` 前，先搜索父策略定义是否带 `&同名anchor`；新增后立即跑 YAML smoke test 再开始 MT5 回测。

### Metadata
- Reproducible: yes
- Related Files: config/strategies.yaml
- See Also: ERR-20260526-001
- Recurrence-Count: 4

---
