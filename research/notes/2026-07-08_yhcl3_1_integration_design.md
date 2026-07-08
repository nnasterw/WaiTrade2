# yhcl 3.1 整合设计: yhcl3.0 + Loop Engineering

**日期**: 2026-07-08
**触发**: 用户要求"整理 loop 的核心策略和优势, 提炼整合进 yhcl3.0 中, 评估改进 yhcl 技能的分析方式, 汇总改进点"
**方法**: 真实数据驱动, 对照 yhcl3.0 (229 变体, 33M token, trend1-553) vs Loop Engineering (_loop.py 5 阶段, 9 个变体, 30 min 时间盒)
**输出**: yhcl 3.1 整合方案 + 10 个具体改进点 + 预期 ROI

---

## 一、yhcl3.0 现状 (从真实运行历史推断)

### 1.1 yhcl3.0 实际工作流

| 阶段 | 动作 | 工具 | 证据 |
|------|------|------|------|
| **调研** | 人工读 76 篇 notes + 用户反馈 | 笔记 + 对话 | `93plus_research_summary.md` |
| **Phase 划分** | 顺序探索, Phase 1-23 | 笔记段落 | `wfyc_88plus_iteration.md` (Phase 1-3 hour filter, Phase 4-5 cap_loss, Phase 6-7 信号源, Phase 8-15 DTP, Phase 16-23 trend298) |
| **批量跑** | Phase 1 = 10 变体一次跑 (trend500-509), Phase 4-5 = 50 变体 (trend218-289) | `mt5_backtest_win.py` | `trend500-553` 共 30+ 变体 |
| **结果归因** | 人工整理, "Phase 1-3 时间过滤灾难", "Phase 4-5 cap_loss 发现" | 笔记中段落 | 22 篇相关 notes |
| **决策** | "继续深挖" 是默认, 没有 4 选 1 Gate | 默认 | `2026-07-04_btc_3perweek_final.md` 结论 |
| **失败处理** | 整个 Phase 失败才停止 | 笔记章节 | Phase 1-3 失败后开始 Phase 4 |
| **Token 用量** | ~33M (229 变体), 不限量 | 无统计 | `93plus_research_summary.md` |

### 1.2 yhcl3.0 的真实优势

1. **调研深度**: 读 76 篇 notes + 用户反馈循环, 能识别出 "trend218 + max_lot 1.0 = 87.34 hard_pass" 这种隐藏 baseline
2. **意外发现**: 30+ 变体中偶然突破 trend531 (88.84) / trend409 (89.21), 验证了"广撒网"的价值
3. **阶段式演进**: Phase 1-23 的递进结构清晰, 每阶段基于上阶段结果调整
4. **EA 源码级突破**: Phase B (BigWinLock, MonthlyLossGuard) 跳出了"参数层"思维
5. **领域词汇沉淀**: 通过 notes 沉淀了 bounce_ob sweet spot / HTF skip / big_w 上限 等术语

### 1.3 yhcl3.0 的真实缺陷 (从踩坑案例倒推)

| 缺陷 | 证据 | 后果 |
|------|------|------|
| **无时间盒** | trend218-429 共 229 变体, 33M token | 月度归因笔记才意识到"突破 89.21 = 评分上限" |
| **无 smoke test** | Phase 1 trend221-229 跑空 (.ex5 未编译支持) | 8+ 小时 token 浪费 |
| **无 cache 清理** | `Phase 3 hour filter` 多变体结果相同 = cache 命中 | 同一结果重复记录, 误导归因 |
| **无 baseline 校验** | 89.21 上限发现过晚 | 应该在 Phase 5 (trend298 = 88.29) 就发现 |
| **假设来源不稳** | Phase 6-7 信号源扩展 = 噪声增加 (121 trades 43% WR) | FVG/MicroBOS 全开退步 |
| **失败处理慢** | Phase 1-3 跑了 30 变体才发现 hour filter 错杀 | 8+ 小时后才停止 |
| **无结构化沉淀** | 笔记段落式记录, 无假设验证表 | 跨 session 容易重复决策 |

---

## 二、Loop Engineering 核心能力提炼

### 2.1 Loop 6 大支柱

| 支柱 | 实现位置 | 关键代码 | 价值 |
|------|----------|----------|------|
| **Preflight** | `_loop_preflight.py` | 6 项检查: 备份/terminal/cache/baseline/user proc/port | 防环境异常 |
| **Diagnose** | `_loop_diagnose.py` | 读 handoff + WFYS 历史 → 3-5 ranked 假设 | 减少盲目设计 |
| **Batch** | `_loop_batch.py` | smoke(30d) → 720d → WFYS + 30 min 时间盒 + cache 清理 | 防 token 爆炸 + 失败即停 |
| **Close** | `_loop_close.py` | _reflect.md (验证表+坑) + _gate.md (4 选 1) + _handoff.md (接力) | 跨 session 沉淀 |
| **Baseline regression** | `_loop_preflight.py` `check_baseline()` | trend218 .set 存在性检查 | 防 MT5 cache 污染 |
| **30 min 时间盒** | `_loop_batch.py` `time-limit=30` | 每 Loop 30 min 硬限制 | 防 yhcl2 类灾难性投入 |

### 2.2 Loop 已经"防住" 的踩坑 (对比 yhcl3.0)

| 踩坑类型 | yhcl3.0 案例 | Loop 防法 |
|----------|--------------|------------|
| Cache 命中 | Phase 3 hour filter 多变体相同 | 每变体前 `clear_mt5_cache()` |
| 时间爆炸 | 33M token 才停 | 30 min 时间盒 |
| Smoke 跑空 | trend221-229 8 小时浪费 | `smoke_test()` 30d fail-fast |
| Baseline 污染 | 89.21 上限发现过晚 | `check_baseline()` trend218 $7,615 ± 0.5 |
| 失败即停 | Phase 1-3 跑完才停 | smoke 不通过即 continue |
| 跨 session 丢失 | 靠会话记忆 | `_handoff.md` 显式接力 |

---

## 三、yhcl 3.1 整合方案

### 3.1 工作流设计 (5 阶段)

```
[Stage 0: Diagnose] (yhcl 调研 + Loop 自动化)
  0.1 读最近 _handoff.md (接力上轮)
  0.2 读 76 篇 research/notes/*.md 提取瓶颈
  0.3 读 WFYS JSON 历史 (trend*_wfys_*.json) 识别趋势
  0.4 生成 3-5 ranked 假设 (含来源引用 notes path)
  0.5 用户审阅 → 4 选 1 Gate 决策

[Stage 1: Preflight] (Loop 引入)
  1.1 6 项环境检查 (备份/terminal/cache/baseline/user proc/port)
  1.2 baseline regression (trend218 = $7,615 ± 0.5)
  1.3 cache 强制清理 (--cleanup-cache)

[Stage 2: Batch] (yhcl 风格 + Loop 纪律)
  2.1 每个变体先 30d smoke test (yhcl3.0 跳过)
  2.2 通过的跑 720d + WFYS 评分
  2.3 30 min 时间盒硬限制 (yhcl3.0 无)
  2.4 每变体后 cache 清理 (防命中)
  2.5 失败即停 (单变体失败 continue, 整批失败 timeout)

[Stage 3: Reflect] (Loop 引入)
  3.1 写 _reflect.md (假设验证表 + 实战坑 + 新发现)
  3.2 写 _gate.md (4 选 1: 继续深挖 / 切换假设 / 重构架构 / 停止)
  3.3 写 _handoff.md (跨 session 接力)

[Stage 4: Close-out] (yhcl 沉淀 + Loop 反思)
  4.1 更新 CONTEXT.md (新术语, 新决策)
  4.2 更新 strategies.yaml (新增变体)
  4.3 备份 yaml + .set 到 temp/loop_engineering_baseline_YYYY-MM-DD/
  4.4 git commit + push (分支 codex/yhcl31-*)
```

### 3.2 命名约定

- **阶段 (Phase)** 保留 yhcl3.0 命名: Phase 1-23 编号
- **Loop** 保留 Loop 命名: loop_1, loop_2, loop_3
- **yhcl 3.1 Phase N Loop M**: 第 N 个 yhcl Phase 的第 M 个 Loop
  - 例: `yhcl-3.1-Phase-24-Loop-1` = 突破 trend218 的第 1 个 Loop

### 3.3 决策矩阵 (4 选 1 Gate)

| Gate | 触发条件 | 行动 |
|------|----------|------|
| **继续深挖** | 当前方向 score 接近 trend218 (87.34) | 同 Phase 跑下一个 Loop |
| **切换假设** | 当前方向 3+ Loop 无进展 | 换新 Phase, 重新 Diagnose |
| **重构架构** | 触及 anchor 锁死 (loop1/loop2 = yhcl1 等价) | 改 EA 源码 / 换 anchor |
| **停止** | 已达目标 / 时间盒用尽 / 突破无望 | 写 Final Report, 收尾 |

---

## 四、10 个具体改进点

### 改进 1: 结构化沉淀 (3 件套笔记)

**现状**: yhcl3.0 笔记散落 (76 篇 `research/notes/*.md`), 无统一模板
**改进**: Loop 风格的 `_reflect.md` / `_gate.md` / `_handoff.md` 三件套
**实施**:
- 在 `research/loops/` 建立 `YYYY-MM-DD_yhcl31_phase_N_loop_M_{reflect,gate,handoff}.md`
- `_reflect.md` 模板: 假设验证表 (ID/变体/预期/实际/状态) + 实战坑 + 新发现
- `_gate.md` 模板: 4 选 1 决策 + 理由 + 后续行动
- `_handoff.md` 模板: 当前最佳 + 未解决 + 下 Loop 接力 + 已排除方向

**预期 ROI**: 跨 session 不丢上下文, 减少 50% 重复决策

### 改进 2: 30 min 时间盒

**现状**: yhcl3.0 33M token, 229 变体无限制
**改进**: 每个 Phase 单 Loop 30 min 时间盒硬限制
**实施**:
- 复用 `_loop_batch.py` 的 `time-limit=30`
- 每个 Loop 跑完即停, 即使未完成全部变体
- 时间盒用尽自动写 _reflect.md (含"时间盒用尽"实战坑)

**预期 ROI**: 防止 yhcl2 类 (DTP+monthly_defensive) 30 min 灾难性投入

### 改进 3: 30d smoke test

**现状**: yhcl3.0 直接跑 720d, trend221-229 8 小时浪费 (Phase 1 hour filter)
**改进**: 每个变体先跑 30d smoke test
**实施**:
- smoke test 命令: `mt5_backtest_win.py --days 30`
- 通过条件: `余额 >= baseline * 0.5` 或 `trade_count >= 5`
- 失败: continue 到下一个变体, 记录到 _reflect.md "smoke 失败" 行

**预期 ROI**: 节省 70% token (30d vs 720d), 早发现 80% 灾难性变体

### 改进 4: MT5 cache 自动清理

**现状**: yhcl3.0 Phase 3 hour filter 多变体结果相同 (cache 命中), 误导归因
**改进**: 每个变体跑完后强制清理 cache
**实施**:
- 复用 `_loop_batch.py` 的 `clear_mt5_cache()`: 删除 `*.tst` 和 `Tester/cache/`
- 在 strategies.yaml 改动前先 cleanup (避免 MT5 命中旧 .set)

**预期 ROI**: 消除 cache 污染导致的"假阴性"和"假阳性"

### 改进 5: Baseline regression

**现状**: yhcl3.0 在 Phase 5 才偶然发现 trend218 = 87.34 hard_pass
**改进**: 每个 Loop 启动前跑 trend218 验证 baseline
**实施**:
- 复用 `_loop_preflight.py` 的 `check_baseline()`
- 验证条件: `trend218 backtest balance ∈ [7500, 7700]` (允许 ±1%)
- 不通过: 警告用户 MT5 cache 污染, 拒绝跑新变体

**预期 ROI**: 提前发现 MT5 异常, 防止 89.21 上限发现过晚

### 改进 6: Diagnose 自动化 (读 76 篇 notes)

**现状**: `_loop_diagnose.py` 只看 WFYS JSON, 完全忽略 notes
**改进**: 扩展为读 `research/notes/*.md` 自动提取候选变量
**实施**:
- 用关键词扫描: `瓶颈` / `上限` / `锁死` / `disaster` / `breakthrough`
- 提取 top_drags 关联的变量 (如 "big_w 上限" → bounce_ob / HTF target)
- 输出格式: 假设 #N (来源: notes/2026-07-04_xxx.md line 23)

**预期 ROI**: 假设质量提升, 减少 30% 盲目设计

### 改进 7: 4 选 1 Gate 决策

**现状**: yhcl3.0 默认"继续深挖", 缺乏明确决策框架
**改进**: 每个 Phase 结束强制 4 选 1
**实施**:
- `_gate.md` 模板固定 4 选项
- 用户必须选择 (含自动推荐)
- "继续深挖" 需提供具体下阶段方向
- "停止" 需提供当前最佳 + 已排除方向

**预期 ROI**: 减少无限期投入, 提前发现"已触顶"信号

### 改进 8: 跨 session 接力 (_handoff.md)

**现状**: yhcl3.0 跨 session 靠人工记忆, 容易重复决策
**改进**: 每个 Loop 写 _handoff.md 给下一个 session
**实施**:
- 模板: 当前最佳 (score + balance) + 未解决 (ranked) + 下 Loop 接力 + 已排除方向
- 下一个 session 启动时自动读最近 _handoff.md

**预期 ROI**: 减少 60% 重复调研时间

### 改进 9: 失败即停 (单变体)

**现状**: yhcl3.0 整个 Phase 跑完才停 (Phase 1-3 跑了 30 变体才发现错杀)
**改进**: 单变体失败 (smoke / 编译错误 / 参数无效) 即 continue
**实施**:
- `_loop_batch.py` 已实现: `if not ok: continue`
- 失败次数 > 50% 触发"整批失败"警告 → Gate 决策

**预期 ROI**: 早发现错杀, 节省 40% Phase 时间

### 改进 10: Token 预算可见化

**现状**: yhcl3.0 33M token 后才发现预算爆
**改进**: 每个 Loop 实时统计 token 用量
**实施**:
- 估算: `30d smoke ≈ 1M token, 720d = 5M, WFYS = 0.5M`
- Loop 默认 30 min / 4 变体 = ~26M token, 接近上限
- 超出 80% 自动警告, 100% 自动停止

**预期 ROI**: 防止 token 意外超支, 提前调整 Phase 规模

---

## 五、改进点优先级矩阵

| 优先级 | 改进点 | 实施难度 | 预期 ROI | 立即可做 |
|--------|--------|----------|----------|----------|
| **P0** | #2 30 min 时间盒 | 低 (复用现有) | 高 (防 yhcl2 灾难) | ✅ |
| **P0** | #3 30d smoke test | 低 (复用现有) | 高 (省 70% token) | ✅ |
| **P0** | #4 MT5 cache 清理 | 低 (复用现有) | 中 (防污染) | ✅ |
| **P0** | #5 Baseline regression | 低 (复用现有) | 中 (防 cache 异常) | ✅ |
| **P1** | #1 结构化沉淀 (3 件套) | 中 (需模板) | 高 (跨 session) | ✅ (复用 _loop_close) |
| **P1** | #8 跨 session 接力 | 中 (需模板) | 中 (减少重复) | ✅ (复用 _handoff) |
| **P1** | #7 4 选 1 Gate | 中 (需用户决策模板) | 中 (明确决策) | ✅ (复用 _gate) |
| **P2** | #6 Diagnose 自动化 | 高 (需 NLP/keyword) | 高 (假设质量) | ⚠️ 渐进 |
| **P2** | #9 失败即停 | 低 (复用现有) | 中 (早发现) | ✅ (已实现) |
| **P2** | #10 Token 预算可见化 | 中 (需估算公式) | 低 (辅助) | ⚠️ 渐进 |

**立即可做 (P0+P1, 共 7 项)**: 全部复用 _loop.py 现有实现, 只需改 yhcl 启动命令为 `_loop.py run`

---

## 六、yhcl 3.1 启动命令 (一键)

```bash
# yhcl 3.1 启动命令 (完整流程)
python scripts/_loop.py run \
  --variants yhcl31-phase-N-loop-M-var1,yhcl31-phase-N-loop-M-var2 \
  --loop-id N --terminal mt5_portable_btc_trend111 \
  --time-limit 30 --gate "继续深挖" --reason "突破 trend218 87.34"

# 单独诊断
python scripts/_loop.py diagnose
# (升级后: 自动读 76 篇 notes 提取瓶颈, 不再只生成 loop550/loop551)

# 单独环境检查
python scripts/_loop.py preflight --cleanup-cache
```

---

## 七、预期效果 (vs yhcl3.0)

| 维度 | yhcl3.0 | yhcl 3.1 (预计) | 改进 |
|------|---------|-----------------|------|
| **平均 token/变体** | 144k (33M/229) | ~50k (含 smoke) | **-65%** |
| **Phase 时间** | 8+ 小时 (Phase 1 hour filter) | <2 小时 | **-75%** |
| **灾难发现时间** | Phase 跑完 (8 hr 后) | 30d smoke (5 min) | **-99%** |
| **跨 session 接力** | 靠记忆 | _handoff.md 显式 | **+∞** |
| **决策明确性** | "继续深挖" 默认 | 4 选 1 强制 | **+显著** |
| **可重复性** | Phase 1-23 笔记 | 3 件套 + JSON | **+显著** |
| **突破能力 (>87)** | trend409 = 89.21 (偶然) | 仍依赖广撒网 | **持平** |

**核心结论**:
- yhcl 3.1 = yhcl3.0 调研深度 + Loop 执行纪律
- **不削弱** yhcl 的"广撒网突破能力", 但**显著降低** token 浪费和踩雷风险
- **立即可实施**: 7 项改进点全部复用 _loop.py 现有实现, 只需 30 min 改造

---

## 八、关键风险与缓解

| 风险 | 缓解 |
|------|------|
| **30 min 时间盒误伤广撒网** | 时间盒仅限"单 Loop", Phase 跨多个 Loop 不限 |
| **Diagnose 自动化生成假设质量差** | 渐进实施, 先 keyword 提取, 后续 LLM 总结 |
| **3 件套笔记增加 token 消耗** | 模板化生成, 不增加人工输入 |
| **用户对 4 选 1 决策疲劳** | 默认推荐"继续深挖", 用户可一键接受 |
| **smoke test 误杀"前期失败后期突破"** | smoke 阈值放宽到 balance >= baseline * 0.3 |

---

## 九、与既有成果的兼容性

| 既有成果 | 兼容性 |
|----------|--------|
| `loop_engineering_baseline_2026-07-07/` | ✅ 完全保留 (git branch) |
| `research/loops/loop_1_*.md` | ✅ 复用为 yhcl 3.1 模板 |
| `scripts/_loop*.py` | ✅ 直接复用, 无需改动 |
| 76 篇 `research/notes/*.md` | ✅ 自动被 Diagnose 读取 |
| `strategies.yaml` (43217 行) | ✅ 直接追加 yhcl-3.1-* 变体 |
| `results/backtest/*_wfys_*.json` | ✅ 自动被 Diagnose 读取 |

---

## 十、3 步立即启动

```bash
# 步骤 1: 验证 Loop 现有能力 (1 分钟)
python scripts/_loop.py preflight --cleanup-cache

# 步骤 2: 跑一个示例 Loop 验证 (5 分钟)
python scripts/_loop.py run \
  --variants v11-btc1-loop1,v11-btc1-loop2 \
  --loop-id 2 --terminal mt5_portable_btc_trend111 \
  --time-limit 30 --gate "继续深挖" --reason "验证 yhcl 3.1 整合"

# 步骤 3: 升级 _loop_diagnose.py 读 notes (30 分钟, 渐进)
# 编辑 _loop_diagnose.py 增加 read_research_notes() 函数
# keyword 扫描: "瓶颈" "上限" "锁死" "突破" "灾难"
# 输出 ranked 假设含来源引用
```

---

## 备份状态

- 本笔记: `research/notes/2026-07-08_yhcl3_1_integration_design.md`
- 依赖脚本: `scripts/_loop.py`, `scripts/_loop_{preflight,diagnose,batch,close}.py`
- 数据基础: `results/backtest/*_wfys_*.json` (221 个) + `research/notes/*.md` (76 篇)
- 回滚点: git branch `loop-engineering-baseline-2026-07-07` + `temp/loop_engineering_baseline_2026-07-07/`

## 一句话总结

**yhcl 3.1 = yhcl3.0 调研深度 + Loop 执行纪律**: 保留 yhcl 的"Phase 划分 + 76 篇 notes 调研 + 广撒网突破" 能力, 引入 Loop 的"30 min 时间盒 + smoke test + cache 清理 + baseline regression + 3 件套沉淀", 7 项 P0+P1 改进全部复用现有 _loop.py, 30 分钟内可启动。
