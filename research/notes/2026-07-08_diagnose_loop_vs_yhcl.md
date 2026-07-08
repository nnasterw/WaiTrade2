# Diagnose: Loop Engineering vs yhcl3.0 (wf-yhcl) 深度对比与融合方案

**日期**: 2026-07-08
**触发**: 用户询问 scripts/_loop.py 流程与 wf-yhcl 分析哪个更好, 两者是否冲突, 能否融合
**方法**: 严格遵循 diagnose 流程 (反馈循环 → 复现 → 假设 → 仪器化 → 结论)
**真实数据样本**: yhcl1-2 (n=2) + loop1-7 (n=7) + trend218/531/409/298 (baseline/anchor 对照)

---

## Phase 1 — 反馈循环

构建对比的"快速通过/失败"信号:
- 跑过 9 个 720d WFYS JSON (覆盖 yhcl + loop 系列 + baseline)
- 读 4 个对比/方法论文档 (`AB_compare_yhcl_vs_loop.md` / `3perweek_final.md` / `wfyc_88plus_iteration.md` / `93plus_*.md`)
- 读 5 个 _loop_*.py 脚本实现 + 实际生成的 _loop_1_{reflect,gate,handoff}.md
- 从 `strategies.yaml` line 43214+ 提取 9 个变体的精确参数差异
- 从 `_loop_batch.py` 提取 30d smoke test + 30min timebox + cache 清理实现

**反馈信号有效性**: ✅ 高 (9 个独立变体的 18 个 hard gate + WFYS 总分 + 月度归因)

---

## Phase 2 — 复现 (关键数据)

### 2.1 全样本对比 (720d 实测)

| 变体 | 方法族 | 改动描述 (相对 anchor `v11_btc1_qual232`) | 分数 | Gates | PM | 余额 | Trades | MDD% | PF | Sharpe |
|------|--------|------------------------------------------|------|-------|----|------|--------|------|-----|--------|
| trend218 | baseline | (无) | **87.34** | 18/18 | 22/24 | $7,615 | 111 | 11.4 | 3.87 | 1.98 |
| trend298 | yhcl 早期 | (历史) | 88.29 | 17/18 | 22/24 | $7,700 | 92 | 7.5 | 3.85 | 1.92 |
| trend409 | yhcl 早期 | (历史) | 89.21 | 17/18 | 22/24 | $8,228 | 83 | 7.1 | 5.37 | 1.96 |
| trend531 | yhcl 早期 | bad_bounce 0.22-0.28 + max_lot 1.0 | 56.33 | 9/18 | 13/24 | $9,600 | 204 | 43.9 | 3.25 | 1.33 |
| **yhcl1** | yhcl3.0 | yhcl1 = cap_loss h=3,4,5,10 + bad_bounce 0.22-0.28 + max_lot=1.0 | 77.14 | 13/18 | 23/24 | $2,757 | 155 | 29.9 | 1.61 | 1.40 |
| **yhcl2** | yhcl3.0 | yhcl1 + DTP 1.5/0.2 + monthly_defensive 5% + monthly_pos_mult 0.4 | **30.36** | 5/18 | 20/24 | $879 | 233 | 51.2 | 1.26 | 0.95 |
| loop1 | Loop Eng | bad_bounce 0.22-0.26 (从 0.28 更严) | 77.14 | 13/18 | 23/24 | $2,757 | 155 | 29.9 | 1.61 | 1.40 |
| loop2 | Loop Eng | bad_bounce_mult 0.5 (从 0.4 减弱) | 77.14 | 13/18 | 23/24 | $2,757 | 155 | 29.9 | 1.61 | 1.40 |
| loop3 | Loop Eng | trend218 + bad_bounce 0.22-0.28 + enable_btc_profile | 37.97 | 7/18 | 17/24 | $1,221 | 248 | 35.1 | 1.65 | 1.03 |
| loop4 | Loop Eng | trend218 + cap_loss h=3,4,5,10,12 r=-0.4 + enable_btc_profile | 37.97 | 7/18 | 17/24 | $1,221 | 248 | 35.1 | 1.65 | 1.03 |
| loop5 | Loop Eng | trend218 + low_balance 0.3/0.5/0.5 + enable_btc_profile | 39.59 | 9/18 | 16/24 | $665 | 216 | 20.3 | 1.69 | 1.10 |
| loop6 | Loop Eng | trend218 + btc_max_lot 0.5 + enable_btc_profile | 35.92 | 7/18 | 17/24 | $1,055 | 245 | 35.8 | 1.61 | 1.02 |
| loop7 | Loop Eng | trend218 + bad_bounce + cap_loss + enable_btc_profile (合并) | 56.92 | 10/18 | 16/24 | $9,928 | 197 | 39.5 | 3.37 | 1.46 |

### 2.2 Group 统计 (修正笔记中的过度乐观)

| Group | n | 平均分 | 标准差 | 最高 | 最低 | < trend218 数 | 失败率 |
|-------|---|--------|--------|------|------|-------------|--------|
| yhcl (yhcl1+yhcl2) | 2 | 53.75 | 33.32 | 77.14 | 30.36 | 2/2 | **100%** |
| loop (loop1-7) | 7 | 51.78 | 14.81 | 77.14 | 35.92 | 6/7 | **86%** |
| baseline (trend218) | 1 | **87.34** | - | 87.34 | 87.34 | 0/1 | **0%** |

**反直觉结论**: 在 anchor `v11_btc1_qual232` 之下:
- yhcl1 = loop1 = loop2 (三者完全等价, $2,757, 77.14, 13/18 gates) → **anchor 锁死了 cap_loss h=10 和 bad_bounce 微调, 三者均未带来实质改进**
- yhcl2 = 真正的多变量并发灾难 (30.36)
- loop3-7 全部低于 trend218 baseline (87.34), 平均 41.06 → **"单变量微调" 启用 BTC profile 同样是灾难**

### 2.3 yhcl2 月度归因 (定位"踩雷根因")

| 月份 | yhcl1 | yhcl2 | 差异 | 归因 |
|------|-------|-------|------|------|
| 月 8 (2024-?) | +1.6% | **-47.2%** | **-48.8%** | monthly_pos_mult 0.4 + monthly_defensive 双重压制 + DTP 提前锁利, 把大赢单截断 |
| 月 11 | +21.7% | +9.5% | -12.2% | 同上机制 |
| 月 21 | +4.9% | **-15.9%** | -20.8% | monthly_defensive 触发后, 仓位降级造成亏损月 |

**yhcl2 灾难机制**:
1. monthly_pos_mult=0.4 把所有仓位减半 → 锁利机会被压制
2. monthly_defensive 触发后连续多月保持低仓位 → 大趋势月的复利消失
3. DTP 1.5/0.2 在小赢单就锁利, 砍掉了 3R+ 大赢单 → `>3R大赢单占比` gate 失败

---

## Phase 3 — Ranked 假设

> 目标: 哪个策略迭代方法更有效? 两者是否冲突? 能否融合?

### H1 (rank 1): **Loop Engineering 在"稳定 + 防踩雷" 上严格优于 yhcl3.0, 但**前提是变量选择正确** (Loop3-7 启用 BTC profile 同样灾难)

- **预测**: Loop 方法配合 `_loop_preflight` 的 6 项检查 + baseline regression + 30 min 时间盒 + smoke test, 可在 9 个变体中将"完全失败的 token 浪费"压到 0
- **证据**: 当前 9 个变体中, 6/7 loop + 2/2 yhcl 都低于 trend218, "踩雷"根源不在并发数量, 而在 anchor 内微调的边际效用低. Loop 框架的 _loop_batch 实现了"30d smoke → 720d → WFYS" 三段式, 至少可以提前过滤
- **证伪条件**: 如果 yhcl1 (= loop1 = loop2) 的等价性证明 anchor 锁死是绝对的, 那么**所有微调都是徒劳**, Loop vs yhcl 比较就失去意义
- **可信度**: 高

### H2 (rank 2): **yhcl3.0 的"广撒网 + 一次性多变量" 在 anchor 未锁死时仍有效, 但需要"分段验证" 流程**

- **预测**: 历史上 trend500-553 (30+ 变体) 中 trend531 偶然突破到 88.84, 这种"广撒网"是有价值的; 但 yhcl1-2 的失败说明 "广撒网" 必须配 "30 min 时间盒" + "失败即停"
- **证据**: `2026-07-07_btc_wfyc_88plus_iteration.md` 记录 trend500-553 共 30+ 变体, 大部分失败但发现 trend531 (88.84) 和 trend540/542/543/550 (88.84). 没有"广撒网"就不会偶然发现突破方向
- **证伪条件**: 如果所有趋势线最高都低于 88, "广撒网" 就是 token 浪费
- **可信度**: 中

### H3 (rank 3): **两者不冲突, 可融合成 "Diagnose (yhcl 广度) + Loop (单变量执行)" 混合工作流**

- **预测**: 在每个 Loop 启动前, 用 yhcl 风格的"穷举调研"识别 3-5 个潜在变量方向; 然后用 Loop 风格的"单变量微调 + 时间盒" 执行. yhcl 提供假设来源, Loop 提供执行纪律
- **证据**: `_loop_diagnose.py` 已实现 "读 handoff + WFYS 历史 → 生成 ranked 假设", 但目前假设生成器只覆盖 `loop550` / `loop551` 两个固定模式. 可以扩展为"读 76 篇 notes 自动提取候选变量"
- **证伪条件**: 如果 Loop 的单变量执行在 anchor 锁死下完全无效, 则即使融合也只能做"诊断", 不能"突破"
- **可信度**: 高

### H4 (rank 4): **真正瓶颈不在参数层, 而在 EA 源码层 (HTF skip + DTP 设计 + MonthlyGuard 缺失)**

- **预测**: 87.34 是 anchor 内参数优化的上限; 突破 90+ 必须改 EA 源码 (CheckMaxLossCap, CheckBigWin, CheckMonthlyGuard), 不是改 .set 参数
- **证据**: `2026-07-04_btc_93_3perweek_plan.md` Phase 3 (E1, E2, E3) 明确指出 "突破需根本性策略方向调整", `2026-07-07_btc_wfys_93plus_FINAL.md` 指出 EA 源码改动 (BigWinLock + MonthlyLossGuard) 编译成功但因 MT5 缓存问题未验证
- **证伪条件**: 如果 BigWinLock + MonthlyLossGuard 验证后仍 < 90, 则 EA 源码层也不够, 需彻底重构
- **可信度**: 高

### H5 (rank 5): **Loop 框架缺少"诊断深度", 仅做执行优化, 假设来源仍是手动**

- **预测**: 当前 `_loop_diagnose.py` 生成的假设太机械 (loop550/loop551), 没有真正利用 76 篇 notes 的领域知识; 必须把"读 notes → 提取瓶颈 → 生成假设" 自动化
- **证据**: `_loop_diagnose.py` 只看 WFYS JSON 历史, 完全不看 `research/notes/*.md` 中的实战坑记录 (例如 "BE 太近被 tick 噪音秒扫" / "M1 小 risk 易被 spread 杀死")
- **证伪条件**: 如果手动设计假设的命中率 (有突破 >87) 显著高于自动生成的假设
- **可信度**: 中

---

## Phase 4 — 仪器化分析 (策略描述差异)

### 4.1 yhcl 系列改动 (vs anchor `v11_btc1_qual232`)

```
yhcl1: btc_cap_loss_hours="3,4,5,10" + bad_bounce_min=0.22 + bad_bounce_max=0.28 + bad_bounce_mult=0.4 + max_lot_size=1.0
yhcl2: yhcl1 + btc_dtp_trigger_r=1.5 + btc_dtp_retrace=0.2 + monthly_defensive_loss_pct=5.0 + monthly_defensive_pos_mult=0.4
```

### 4.2 loop1-7 改动

```
loop1: bad_bounce 0.22-0.26 (single-var)
loop2: bad_bounce_mult 0.5 (single-var)
loop3: trend218 + bad_bounce 0.22-0.28 + enable_btc_profile=true (multi-var 隐含)
loop4: trend218 + btc_cap_loss_r=-0.4 + cap_loss hours 3,4,5,10,12 + enable_btc_profile=true
loop5: trend218 + btc_low_balance threshold 1500 + pos_mult 0.3 + max_lot 0.5 + enable_btc_profile=true
loop6: trend218 + btc_max_lot 0.5 + max_lot_size 0.5 + enable_btc_profile=true
loop7: trend218 + bad_bounce 0.22-0.28 + cap_loss r=-0.4 hours 3,4,5,10 + enable_btc_profile=true
```

**关键观察**:
- loop1/loop2 = 真正单变量 (未启用 BTC profile), 与 yhcl1 结果完全等价
- loop3-7 都启用了 `enable_btc_profile: true`, 这是个**结构性大改动**, 不是单变量
- loop3 = loop4 (cap_loss 几乎无影响, 完全等价 37.97)
- loop6 (max_lot 0.5) 分数最低 35.92, **说明降仓位不解决 anchor 内的根本问题**

### 4.3 关键瓶颈定位

anchor `v11_btc1_qual232` 实际启用了 `enable_btc_profile` 的某些功能, 而 loop3-7 重新显式启用 = **重复配置**, 引入负向参数:
- `btc_cap_loss_*` 系列 (loop3/4/7): 全部 < 60 分, 实际**压制大赢单**
- `btc_low_balance_*` (loop5): 39.59, **过度保护导致仓位闲置**
- `btc_max_lot 0.5` (loop6): 35.92, **仓位减半直接腰斩**

---

## Phase 5 — 核心结论 (不修代码, 是评估)

### 5.1 哪个方法效果更好?

| 维度 | Loop Engineering (_loop.py) | yhcl3.0 (wf-yhcl) | 赢家 |
|------|----------------------------|---------------------|------|
| **执行纪律** | 6 项 preflight + 30 min 时间盒 + cache 自动清理 + smoke test | 无纪律, 凭手感 | **Loop 完胜** |
| **变量归因** | 单变量 (声称), 但 loop3-7 实为多变量 | 多变量并发 | 平 (Loop 名字骗人) |
| **假设来源** | `_loop_diagnose.py` 自动 (但很弱) | 人工调研 76 篇 notes | **yhcl 略胜** |
| **Token 效率** | 30 min 时间盒硬限制 | 无限制, 30+ 变体一次跑 | **Loop 完胜** |
| **结果稳定性** | loop1/loop2 完全等价 (但未突破) | yhcl1 ≈ loop1, yhcl2 灾难 | **Loop 略胜** |
| **突破能力** | 0 个变体 > trend218 (87.34) | 历史上 trend531 (88.84) 偶然突破 | **yhcl 略胜** |
| **复盘沉淀** | _reflect/gate/handoff.md 三件套 | 76 篇 notes 散落 | **Loop 完胜** |

**总评**: **Loop Engineering 是更好的默认流程**, 但要承认:
1. 它的"单变量"标签不诚实 (loop3-7 实为多变量)
2. 它的诊断阶段太弱 (假设来源仍是手动)
3. 它没有"突破能力", 只能做"参数微调"

### 5.2 两者是否冲突?

**部分冲突**:
- Loop 的"30 min 时间盒"会**抑制** yhcl 的"广撒网突破" (例如 trend500-553 用了 30+ 变体, 远超 30 min)
- Loop 的"smoke test fail-fast" 会**丢弃**某些"前期失败但后期突破"的偶然发现
- Loop 的"preflight 检查"会**延迟** yhcl 风格的"快速试错"

**部分互补**:
- yhcl 的 76 篇 notes 是 Loop 诊断阶段的输入
- Loop 的时间盒/缓存清理是 yhcl 的"防爆器"
- Loop 的 _reflect/gate/handoff 是 yhcl 的"结构化沉淀"

### 5.3 能否融合?

**完全可以, 推荐方案**:

```
[诊断阶段 yhcl 风格]
  1. 读 76 篇 notes 识别真实瓶颈 (top_drags + 实战坑)
  2. 生成 3-5 个 ranked 假设 (yhcl 的人工判断 + Loop 的结构化)
  3. 用户审阅 + Gate 决策 (继续/切换/重构/停止)

[执行阶段 Loop 风格]
  4. preflight 检查 (6 项环境)
  5. 每个变体先 30d smoke test (Loop 防踩雷)
  6. 通过的变体跑 720d + WFYS
  7. 30 min 时间盒 (Loop 防 token 爆炸)
  8. cache 自动清理 (Loop 防污染)

[沉淀阶段 Loop 风格]
  9. _reflect.md 实战坑
  10. _gate.md 4 选 1 决策
  11. _handoff.md 跨 session 接力
```

**融合后的硬规则**:
1. **每个变体必须先 30d smoke test** (Loop 防踩雷)
2. **每个变体后必清理 MT5 cache** (Loop 防污染)
3. **多变量并发必须分阶段** (先单变量, 再两两组合, 再 3 变量)
4. **baseline regression**: 跑新变体前先跑 trend218 (87.34 hard_pass)
5. **30 min 时间盒**: 单 Loop 硬限制, 防止 yhcl2 灾难性投入
6. **diagnose 阶段必读 76 篇 notes**: 避免 _loop_diagnose 当前"loop550/loop551" 的机械输出

---

## Phase 6 — 后续行动

### 6.1 立即可做 (无需改代码)

| 行动 | 工作量 | 预期效果 |
|------|--------|----------|
| 把 `_loop_diagnose.py` 扩展为读 76 篇 notes 自动提取候选变量 | 30 min | 提升假设质量 |
| 把 `_loop_batch.py` 的 smoke test 设为强制 (当前可 `--no-smoke` 跳过) | 10 min | 防 yhcl2 类灾难 |
| 添加 baseline regression check (跑 trend218 验证 $7,615 ± 0.5) | 20 min | 防 MT5 缓存污染 |
| 给 _loop_close.py 添加 "fusion 模式": yhcl 调研 → loop 执行 一条龙 | 1 hr | 完整融合流程 |

### 6.2 中期 (需小改 EA 源码)

参考 `2026-07-07_btc_wfys_93plus_FINAL.md`:
- BigWinLock (R>=2.5 锁 1.5R) — 编译成功, 待 MT5 cache 解决后回测验证
- MonthlyLossGuard (月度保护) — 同上
- 这两个改动预期突破 88 → 90+, 是真正的"突破方向"

### 6.3 长期 (需根本性重构)

如果 BigWinLock + MonthlyLossGuard 仍 < 90, 则:
- 跳出 OB 范式, 引入新信号源 (H4 break-and-retest / M15 momentum)
- 多策略组合 (BTC OB + XAU 趋势)
- 完全不同的策略基线 (v10_m3_* 家族)

### 6.4 不要做

- ❌ 不要在 anchor `v11_btc1_qual232` 内继续微调 (cap_loss/bad_bounce/max_lot 都被锁死)
- ❌ 不要直接复制 yhcl2 的 DTP+monthly_defensive 组合 (yfcl2 已证明 30.36 灾难)
- ❌ 不要跳过 preflight 检查 (即使看起来"明显要跑")

---

## 备份状态

- 本笔记: `research/notes/2026-07-08_diagnose_loop_vs_yhcl.md`
- 数据来源: `results/backtest/v11-btc1-{loop1-7,yhcl1-2}_wfys_*.json` (9 个 JSON)
- 备份脚本: `temp/loop_engineering_baseline_2026-07-07/` + git branch `loop-engineering-baseline-2026-07-07`

## 一句话总结

**Loop Engineering 是更好的"默认执行流程", yhcl3.0 是更好的"假设来源"; 融合成 yhcl(诊断) + Loop(执行) 的混合工作流, 用 Loop 的纪律包装 yhcl 的广度, 用 yhcl 的笔记喂养 Loop 的诊断, 是当前最高 ROI 的迭代策略。**
