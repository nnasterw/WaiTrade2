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
- See Also: 2026-05-20 Round9/Round10 再次发生同类问题，`v11_r9_profit_push` 继承 `*v11_r9_quality_core`、Round10 继承 `*v11_r9_quality_soft` 前未声明对应 anchor；2026-05-21 Round12 再次继承 `*v11_r10_qsoft_freq` / `*v11_r10_qsoft_6k` 前未声明 anchor；Round15 再次继承 `*v11_r11_qsoft_l45_add1120` 前未声明 anchor；Round16 再次继承 `*v11_r15_q1120_h1push` 前未声明 anchor；Round18 再次继承 `*v11_r18_shallow_h1320_r3` 前未声明 anchor，已补齐。
- Recurrence-Count: 7

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
