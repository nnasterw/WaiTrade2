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
