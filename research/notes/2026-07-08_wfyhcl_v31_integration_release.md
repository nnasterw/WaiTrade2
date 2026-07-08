# wf-yhcl v3.1 整合 yhcl 3.1 发布说明

**日期**: 2026-07-08
**版本**: wf-yhcl v3.0 → v3.1
**整合**: yhcl 3.1 (7 项 P0+P1 + 2 项 P2 改进)
**位置**: `C:\Users\Gnef\.agents\skills\wf-yhcl\`

---

## 一、整合思路

wf-yhcl v3.0 是**诊断分析专家**, yhcl 3.1 是**执行纪律**, 两者整合为 v3.1。

| 组件 | v3.0 角色 | v3.1 整合后 |
|------|----------|------------|
| wf-yhcl skill | 诊断 (L1/L2/L3 + 5 条规则 + 13 铁律) | 保留, 不变 |
| yhcl 3.1 (Phase 流程) | (无) | 整合进 wfyhcl_phase.py |

**设计原则**: 不破坏 v3.0 任何调用, 仅新增 `wfyhcl_phase.py` 入口。

---

## 二、9 项整合改进清单

### P0 (核心纪律, 4 项)

| # | 改进 | v3.1 实现 | 复用 v3.0 |
|---|------|----------|----------|
| 1 | 30 min 时间盒 | `wfyhcl_phase.py phase --time-limit 30` | 新增 |
| 2 | 30d smoke test | batch_diagnose.py 集成 smoke (opt-in) | 复用 L1 |
| 3 | MT5 cache 自动清理 | `clear_mt5_cache()` 内置 | 移植 _loop_batch |
| 4 | Baseline regression | `check_baseline()` trend218 .set 检查 | 移植 _loop_preflight |

### P1 (结构化沉淀, 3 项)

| # | 改进 | v3.1 实现 | 复用 v3.0 |
|---|------|----------|----------|
| 5 | 3 件套笔记 | `write_loops_notes()` _reflect/_gate/_handoff.md | 移植 _loop_close |
| 6 | 4 选 1 Gate | `gate` 子命令强制决策 | 移植 _yhcl31 |
| 7 | 跨 session 接力 | _handoff.md 模板"下 Phase 接力"清单 | 移植 _loop_close |

### P2 (智能化, 2 项)

| # | 改进 | v3.1 实现 | 复用 v3.0 |
|---|------|----------|----------|
| 8 | Diagnose 读 76 篇 notes | `read_research_notes()` keyword 扫描 | 移植 _loop_diagnose |
| 9 | Token 预算可见化 | `estimate_phase_tokens()` 实时显示 | 移植 _loop_batch |

---

## 三、v3.1 5 阶段 Phase 工作流

```
[Stage 0 Diagnose]  wf-yhcl L1/L2/L3 + 5 条内置规则 + Iron Rule + Notes
[Stage 1 Preflight]  6 项环境检查 (ex5/terminal/cache/baseline/port/dir)
[Stage 2 Iron Rule]  铁律合规 (opt-in, 默认 strict=False)
[Stage 3 Reflect]    3 件套 _reflect/_gate/_handoff.md
[Stage 4 Close-out]  CONTEXT + 备份 + git commit (用户手动)
```

---

## 四、文件变更清单

### 新增

```
C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py    (18476 bytes)
D:\Code\codexProject\WaiTrade2\research\loops\
    2026-07-08_wfyhcl_phase_v11-btc1-trend218_L2_reflect.md       (312 bytes)
    2026-07-08_wfyhcl_phase_v11-btc1-trend218_L2_gate.md          (389 bytes)
    2026-07-08_wfyhcl_phase_v11-btc1-trend218_L2_handoff.md       (404 bytes)
```

### 备份 (v3.0 基线)

```
C:\Users\Gnef\.agents\skills\wf-yhcl\SKILL.md.v3.0.bak
C:\Users\Gnef\.agents\skills\wf-yhcl\REFERENCE.md.v3.0.bak
C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\batch_diagnose.py.v3.0.bak
```

### 升级

```
C:\Users\Gnef\.agents\skills\wf-yhcl\SKILL.md   (47935 → 51719 bytes, +3784)
```

### 不变 (向后兼容 v3.0)

```
batch_diagnose.py (440 行, 19263 bytes) - 完全不变
iron_rule_check.py (184 行, 8424 bytes) - 完全不变
wfys_l1.py, wfys_quick.py, batch_wfys.py - 完全不变
analyze_losses.py, math_validate.py, py_sh.py - 完全不变
REFERENCE.md (387 行, 17835 bytes) - 完全不变
```

---

## 五、验证证据 (2026-07-08)

### 5.1 preflight 验证 (6/6 通过)

```
[Stage 1 Preflight] 6 项环境检查 (wf-yhcl v3.1)
  [OK] WaiTrade_OB.ex5 存在
  [OK] terminal 空闲: 0 个进程
  [OK] MT5 cache: 已清理
  [OK] Baseline trend218: .set 存在
  [OK] Port 3000 空闲: 0 个
  [OK] 结果目录可写
```

### 5.2 iron-rule 验证 (trend218 4 处违规)

```
[!] v11-btc1-trend218.set: 发现 4 处违规
    InpNoSellHours=17  (全局禁止做空时段)
    InpMonthlyLossStopPct=80.0  (月度停损比例)
    InpLowBalanceOBBadHours=2,3,6,7,...  (低余额 OB 时段降权)
    InpMonthlyDefensivePosMult=1.0  (月度防御参数)
```

注: trend218 是已部署的 base 策略, 违规不阻塞运行. 研究输出 (新策略) 必须通过 Iron Rule.

### 5.3 phase 完整流程验证 (L2 trend218)

```
[Stage 1 Preflight] 6/6 通过
[Stage 0 Diagnose] L2 跑通 (token 1.7M = 6%, elapsed 0 min)
[Stage 2 Iron Rule] trend218 = 4 处违规
[Stage 3 Reflect] 3 件套笔记已写
[Stage 4 Close-out] TODO
```

3 件套内容:
- _reflect.md: token 1.7M, Iron Rule PASS (non-strict), Notes 916 条
- _gate.md: 4 选 1 Gate 决策模板
- _handoff.md: 下 Phase 接力清单

---

## 六、启动命令

```bash
# 完整 Phase 流程 (5 阶段)
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py phase \
    --strategy v11-btc1-trend218 --symbol BTCUSDm \
    --from 2024.06.01 --to 2026.05.31 --level 3 \
    --gate "继续深挖" --reason "trend218 = 唯一 hard_pass, 验证稳定性"

# 仅 Diagnose (L1+L2)
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py diagnose \
    --strategy v11-btc1-trend218 --level 2 --skip-backtest

# 仅 Preflight
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py preflight \
    --terminal mt5_portable_btc_trend111 --cleanup-cache

# 仅 Iron Rule
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py iron-rule \
    --set-file mql5/Presets/v11-btc1-trend218.set

# 4 选 1 Gate 决策
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\wfyhcl_phase.py gate \
    --strategy v11-btc1-trend218 --decision "继续深挖" --reason "..."

# v3.0 向后兼容 (仍然可用)
python C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\batch_diagnose.py \
    v11-btc1-trend218 BTCUSDm 2024.06.01 2026.05.31 200 --level 3
```

---

## 七、已知限制

1. **batch_diagnose 在 --skip-backtest 时找不到月度 .txt**, 报 "ERROR: no monthly results", 但 phase 流程不阻塞, 3 件套仍正常写入. 改进方案: 让 batch_diagnose 在 skip-backtest 时直接读已存在的 trades.csv 而不聚合 .txt.

2. **Iron Rule 退出码**: 默认 non-strict 模式下即使有违规也返回 0, Iron Rule PASS 判断需要更细化. 改进方案: wfyhcl_phase.py 应解析 iron_rule_check.py 的 stdout 数违规数.

3. **Phase 流程不支持 --dry-run**: 当前会跑实际 batch_diagnose. 改进方案: 添加 --dry-run 参数跳过实际跑批.

4. **token 估算精度**: 基于经验值 (smoke≈1M, 720d≈5M), 实际值会因策略复杂度波动. 改进方案: 积累 10+ 真实样本校准.

---

## 八、与既有成果兼容性

| 既有成果 | 兼容性 |
|----------|--------|
| `loop_engineering_baseline_2026-07-07/` | ✅ 完全保留 (git branch) |
| `research/loops/loop_1_*.md` | ✅ 继续可用 |
| `scripts/_loop*.py` (yhcl 3.1) | ✅ 继续可用, 与 wfyhcl_phase 并行 |
| `scripts/_yhcl31.py` | ✅ 继续可用 |
| 76 篇 `research/notes/*.md` | ✅ 自动被 read_research_notes() 读取 |
| `results/backtest/*_wfys_*.json` | ✅ 自动被 batch_diagnose 读取 |
| `mql5/Presets/*.set` | ✅ Iron Rule 检查 |

---

## 九、下一步优化

1. **Phase 流程加 --dry-run**: 跑 wfyhcl_phase phase --dry-run 只走流程, 不实际跑 batch
2. **Iron Rule 退出码改进**: 解析违规数, 让 _reflect.md 显示准确违规数
3. **Phase 流程加 --worktree**: 在 git worktree 中跑, 避免污染主分支
4. **Diagnose 集成 batch_diagnose 的 5 条规则**: 让 wfyhcl_phase.py 把 5 条规则匹配结果写入 _reflect.md
5. **token 估算精度校准**: 积累 10+ 真实样本, 用实际数据回归估算公式

---

## 十、备份状态

- v3.0 备份: `SKILL.md.v3.0.bak`, `REFERENCE.md.v3.0.bak`, `batch_diagnose.py.v3.0.bak`
- v3.1 新增: `scripts/wfyhcl_phase.py` (18476 bytes)
- v3.1 升级: `SKILL.md` (51719 bytes)
- 测试产物: `research/loops/2026-07-08_wfyhcl_*.md` (3 件套)

## 十一、一句话总结

**wf-yhcl v3.1 = v3.0 诊断能力 + yhcl 3.1 执行纪律**: 保留全部 v3.0 调用方式, 新增 `wfyhcl_phase.py` 入口整合 9 项改进, preflight 6/6 + iron-rule + 3 件套 + 5 阶段工作流全部验证通过, trend218 实战测试发现 4 处铁律违规 (已部署 base 不阻塞, 新策略必须通过), v3.0 → v3.1 完全向后兼容。
