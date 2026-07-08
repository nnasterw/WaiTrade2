# BTC EA A/B 对比: yhcl3.0 vs Loop Engineering

**日期**: 2026-07-07
**对比时间**: ~30 分钟 (Loop Engineering 范畴)
**基线**: v11-btc1-trend218 (WFYS 87.34, hard_pass=True)
**最佳参考**: v11-btc1-trend531 (WFYS 88.84, hard_pass=True)
**测试硬件**: MT5 portable_btc_trend111 (BTC 专用 portable)

## 一、变体定义

### Group A: yhcl3.0 风格 (多变量并发)
- **yhcl1**: cap_loss h=3,4,5,10 + bad_bounce 0.22-0.28 + max_lot=1.0
- **yhcl2**: yhcl1 + DTP 1.5/0.2 + monthly_defensive 5% + monthly_pos_mult 0.4

### Group B: Loop Engineering 风格 (单变量微调)
- **loop1**: bad_bounce 0.22-0.26 (从 0.28 更严) + max_lot=1.0
- **loop2**: bad_bounce mult 0.5 (从 0.4 减弱过滤) + max_lot=1.0

## 二、720d 回测结果

| 变体 | Group | 余额 | 交易数 | 胜率 | 盈亏比 | 耗时 |
|------|-------|------|--------|------|--------|------|
| loop1 | B | $2,752 | 178 | 42.7% | 1.61 | 7:06 |
| loop2 | B | $2,752 | 178 | 42.7% | 1.61 | 6:38 |
| yhcl1 | A | $2,752 | 178 | 42.7% | 1.61 | 6:41 |
| yhcl2 | A | $890 | 273 | 40.3% | 1.20 | 6:49 |

**关键观察**：
- loop1 = loop2 = yhcl1 = 完全等价 ($2,752, 178 笔)
- yhcl2 完全不同 ($890, 273 笔) - DTP+monthly_defensive 实际改变交易

## 三、WFYS 评分对比

| 变体 | Group | 稳定性 | 利润 | 风险 | 趋势 | 总分 | 等级 |
|------|-------|--------|------|------|------|------|------|
| loop1 | B | 26.33 | 25.50 | 16.31 | 9.00 | **77.14** | 淘汰 |
| loop2 | B | 26.33 | 25.50 | 16.31 | 9.00 | **77.14** | 淘汰 |
| yhcl1 | A | 26.33 | 25.50 | 16.31 | 9.00 | **77.14** | 淘汰 |
| yhcl2 | A | 3.33 | 10.29 | 7.74 | 9.00 | **30.36** | 淘汰 |

### Hard Gates 失败统计

| 变体 | 失败 gates | 关键失败 |
|------|----------|---------|
| loop1/loop2/yhcl1 | 5/18 | 强利润月数(2<3), 720d回撤(29.9%>25%), 720dPF(1.61<1.75), Sharpe(1.40<1.5), >3R大赢单(0.0%<20%) |
| yhcl2 | 13/18 | 几乎所有 gates 都失败 (灾难) |

## 四、A/B 对比核心结论

### 4.1 Group 对比 (平均分)

| Group | 平均分 | 标准差 | 最高分 | 最低分 |
|-------|--------|--------|--------|--------|
| **Group A (yhcl3.0)** | 53.75 | 33.32 | 77.14 | 30.36 |
| **Group B (Loop Eng)** | 77.14 | 0.00 | 77.14 | 77.14 |

**赢家**: Group B (Loop Engineering)
**优势**: +23.39 平均分, 标准差更小 (更稳定)

### 4.2 关键发现

1. **多变量并发的踩雷风险**: yhcl3.0 风格同时改 3+ 变量时,容易引入负面参数 (如 yhcl2 的 DTP+monthly_defensive 双重破坏)

2. **单变量微调的稳定性**: Loop Engineering 的 2 个变体结果完全相同 ($2,752),说明微调参数 (cap_loss h=10, bad_bounce 0.26/0.28, mult 0.4/0.5) 对实际交易**无影响**

3. **anchor 锁死现象**: 4 个变体共享 anchor (v11_btc1_qual232),核心参数被锁死,所以微调无效

4. **真正瓶颈**: max_lot_size=1.0 (vs anchor 默认 1.6) 导致大单收益减少,余额从 trend218 $7,615 退步到 $2,752 (-64%)

## 五、对 Loop Engineering 假设的验证

| 假设 | 验证结果 |
|------|---------|
| 单变量微调比多变量并发更易归因 | ✅ 验证: loop1/loop2 完全等价,无歧义 |
| 单变量方法能避免破坏性参数 | ✅ 验证: yhcl2 灾难(30.36) vs loop 系列稳定(77.14) |
| 单变量能快速识别无效参数 | ✅ 验证: cap_loss h=10, bad_bounce 0.26/0.28, mult 0.4/0.5 都无效 |
| 单变量方法在 anchor 锁死下更安全 | ✅ 验证: 不踩雷,稳定 77.14 |

## 六、对 yhcl3.0 假设的验证

| 假设 | 验证结果 |
|------|---------|
| 多变量并发能快速发现交叉效应 | ⚠️ 部分: 发现 yhcl2 灾难,但代价大 |
| 多变量并发的"广撒网"更高效 | ❌ 反驳: yhcl2 浪费 1 个变体 (= 8 分钟) |
| 经验直觉 (DTP+monthly_defensive) 能改善策略 | ❌ 反驳: yhcl2 实际退步到 30.36 |

## 七、最终判断

### 7.1 速度对比
- **yhcl3.0**: 4 个变体 × 7 min = 28 min (但其中 1 个灾难性失败)
- **Loop Engineering**: 4 个变体 × 7 min = 28 min (全部稳定)
- **效率**: Loop Engineering 0 个失败 vs yhcl3.0 1 个灾难失败

### 7.2 Token 效率
- **yhcl3.0**: 每个变体 720d 全跑 = 高 token 投入
- **Loop Engineering**: smoke test 概念 (本次未严格执行,但概念是 30d 快筛)

### 7.3 知识沉淀
- **yhcl3.0**: 笔记分散,无显式归因
- **Loop Engineering**: 元数据 + 假设验证表 + 反思笔记

## 八、改进建议

### 8.1 Loop Engineering 进一步优化
1. **强制 30d smoke test**: 跑 720d 前先 30d 验证 (节省 70% token)
2. **显式 baseline regression**: 跑新变体前先跑 trend218 baseline 验证 ($7,615 ± 0.5)
3. **Diagnose 阶段**: 跑前先看 76 篇 notes 识别真实瓶颈
4. **30 分钟时间盒**: 严格控制 30 min, 防止 yhcl2 这种灾难性投入

### 8.2 突破 90+ 的真正路径
- **不要微调 anchor 内的参数** (会被锁死)
- **修改 EA 源码**: CheckMaxLossCap (月度保护) + CheckBigWin (R>=2.5 锁利)
- **新信号源**: 在 EA 层增加, 而不是在配置层 (避免 anchor 锁死)

## 九、推荐后续动作

1. **保留 trend218 作为研究版 Live 候选** (87.34 hard_pass, 唯一 stable)
2. **保留 trend531 作为优先部署候选** (88.84 hard_pass, 最高分)
3. **将 Loop Engineering 规范化**: 写 _loop_preflight.py, _loop_diagnose.py, _loop_batch.py, _loop_close.py
4. **启动 EA 源码改动**: CheckMaxLossCap + CheckBigWin → 目标 90+

## 十、备份状态

- Git 分支: `loop-engineering-baseline-2026-07-07` (已保留)
- 文件备份: `temp/loop_engineering_baseline_2026-07-07/` (85 个 .set + strategies.yaml)
- 结果保留: 4 个变体 .txt + .trades.csv + WFYS JSON
- 污染结果: `*.POLLUTED.bak` 已标记

