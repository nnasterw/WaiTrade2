# wf-yhcl v3.1 REFERENCE - 按需加载的可复用规律

> 本文档存放主逻辑不需要、但深入诊断需要的可复用规律和方法。
> 加载时机: 用户明确要求深入, 或 L3 自动根因匹配触发对应模式。

---

## §1 每笔订单的独立诊断

### 1.1 HTF 趋势方向判定

\\\python
HTF趋势方向 = sign(sum(N根K线内 看涨推力 - 看跌推力))
  每根K线推力 = (收盘 - 开盘) / ATR
  或: = (最高 - 最低) * (方向实体系数)

trend_alignment(trade):
    m15_dir = m15_trend(trade.entry_time)
    h1_dir  = h1_trend(trade.entry_time)
    trade_dir = 'buy' if buy else 'sell'
    aligned_count = sum(1 for d in [m15_dir, h1_dir] if d == trade_dir)
    return aligned_count  # 0=全逆势 / 1=半对齐 / 2=全对齐
\\\

**可复用规则**: 全对齐入场 WR > 半对齐 > 全逆势, 差值可预期 (不依赖月份)。

### 1.2 OB 信号质量量化

\\\python
ob_quality(ob):
    body_score  = ob.body / ob.range
    size_score  = ob.range / current_atr
    fresh_score = 1 - ob.age / max_age
    bounce_score = bounce_depth
    return 加权平均(四个 score)
\\\

**可复用规则**: 高分组 WR - 低分组 WR > 10% → OB 质量是有效过滤器。

### 1.3 趋势对齐 (低覆盖维度补救)

v11-btc1-trend* backtest_digest 未填充 h1/htf 列,补救方法:
- Excel 透视表: 行=h1, 值=WR(PnL>0%) → 顺势 vs 逆势 WR 差
- 修改 mt5_backtest_win.py 让 backtest_digest 输出 h1/htf

### 1.4 盈利单 R 倍数分布

\\\
微盈(<0.5R) 占比 > 50% → 利润被出场机制切碎
大赢(>3R)   占比 < 5%  → 没有让利润奔跑
分布形态: 指数分布 (健康) vs 集中在左端 (病态)
\\\

### 1.5 入场位置分析

\\\
entry_depth = |entry_price - ob_boundary| / ob_height
depth_bucket = shallow(<0.2) / mid(0.2-0.5) / deep(>0.5)
\\\

### 1.6 盈亏强度比值

\\\
W/L = avg_W / |avg_L|
W/L > 1.5  → 胜率容忍度高
W/L < 0.8  → 数学上负期望
\\\

### 1.7 价格行为结构分析 (高级)

OB 区域交互的 5 种模式:
\\\
模式A: 触及→反弹→继续向OB方向突破 → 亏损  ← 震荡月 83% 概率
模式B: 触及→小幅弹回→继续向突破方向前进 → 盈利
模式C: 在OB内部反复扫荡 → 双向亏损  ← 绞肉区
模式D: 强势突破OB→回踩OB→大幅前进 → 大盈利  ← BOS最佳时机
模式E: 从OB区域反弹→反转突破上方阻力 → 大盈利
\\\

**4580 绞肉区识别**:
\\\
trade_density_Z > 20% AND win_rate_Z < 35% → 绞肉区
验证: 区间内突破(模式D) = 印钞机, 区间内反弹(模式A) = 绞肉机
\\\

### 1.8 结构性级别持久化 (高级)

BOS 突破的结构级别不应随信号过期而消失。4580 案例证明价格可能在数天甚至数周后回踩同一突破位。

**实现**:
- BOS 突破时保存 StructLevel{price, direction, atr, entry_count, last_entry_bar}
- 永不过期,但 30bar 内不重复入场
- 2505 趋势月验证: 结构级别 +71% 利润

---

## §2 Phase 2 扩展 (16 个核心维度)

| # | 维度 | 特征 | 改进 | 关键证据 |
|:---:|------|------|:---|:---|
| 1 | 噪音过滤 | tick 方向比率 | InpSLBufferATR | - |
| 2 | 趋势对齐 | HTF/MTF 净推力 | InpEnableHTFNetPushFilter | - |
| 3 | OB 低质量 | bounce_ob/年龄/实体 | InpMinOBStrength | - |
| 4 | SL 缓冲放宽 | SL 过窄比例 | InpSLBufferATR | - |
| 5 | 微盈修复 | <0.3R 占比 | InpDTPTriggerR 1.5+ | - |
| 6 | 方向偏差 | 单边 PnL | H4 方向锁 | - |
| 7 | 过滤栈逐层 | 各层拦截率 | 绕过/新增入口 | - |
| 8 | 4580 绞肉区 | 区间密度+WR | 限制 OB 交易次数 | 4580 27笔-\ |
| 9 | H1 Swing 结构 | BOS/CHoCH | 结构级别入场 | - |
| 10 | 结构级别持久化 | BOS 突破位有效期 | 永不过期 | 2505: \→\ |
| 11 | H4 方向锁 | H4 趋势方向 | 拦截逆势 Bounce | 2605: -\→-\ (-87%) |
| 12 | 方向 DTP 出口 | 顺势/逆势独立 DTP | InpBuy/SellDTPTriggerR | 2605: 2.0R/0.30 全局比 1.0R/0.20 好 |
| 13 | DTP 多级阶段 | 阶段 2 宽放趋势 | InpDTPStage2TriggerR | 趋势月: 阶段 2 = 6R/0.50 |
| 14 | 双轨并行架构 | BOS+Bounce 独立通道 | 减少互相干扰 | 2505: \ vs \ |
| 15 | 账户规模杠杆 | Min lot vs 余额 | \.5K+ 再回测 | \×0.01=\ / \×0.1=\ |
| 16 | H4 BOS 独立 MaxBars | H4 vs H1 信号配置 | H4: 7200bar / H1: 720bar | 4580 回踩 5 天后 |

**新增假说维度 (BD08 50+ 轮迭代实证)** 见上面 #11-16。

---

## §3 Phase 3 扩展 (数学验证)

### 3.5 双月交叉验证

\\\python
def validate_variant(bd07_2505, bd07_2605, variant_2505, variant_2605):
    v2_improve = variant_2605.net >= bd07_2605.net
    v2_degradation = variant_2505.net >= bd07_2505.net * 0.90
    combined = (variant_2505.net + variant_2605.net) > (bd07_2505.net + bd07_2605.net)
    return v2_improve and v2_degradation and combined
\\\

### 3.6 Scalping 退化检测

\\\
trend_month_pnl_degradation = 1 - (variant_trend / baseline_trend)
  <= 0%  → 完美
  1-10%  → 可接受
  10-30% → 警告
  > 30%  → 拒绝 (Scalping 结构被破坏)
\\\

### 3.7 逐参数迭代法

> **2605 血训: 一次改 5 个参数 → 找不到根因。一次改 1 个 → 定位准确。**

\\\python
variants = [
    Step 1: BD07 EXACT (建立基线)
    Step 2: BD07 + BOS only (纯增量)
    Step 3: BD07 + BOS + bypass 双扫
    Step 4-8: 逐参数微调
]
\\\

### 3.8 50+ 轮迭代收敛定律

> **93% 的参数改动会退化。唯一收敛的路径是结构性的。**

\\\
BD08 50+ 轮迭代收敛记录:
收敛的改动 (7%):
  H4 方向锁 → 2605 -87%, 2505 -87%
  DTP 2.0R/0.30 → 2605 +\ (首次盈利)
  BOS 双轨 → 2505 +71%
  BOS bypass 双扫 → 突破过滤栈

退化/回退的改动 (93%):
  SL 改宽 → 2505 \→\ (-97%)
  TimeExit 延长 → 趋势 scalping 破坏
  H4 Adaptive → 趋势误判为震荡
  BouncePct 变低 → 质量下降
  结构级别直接入场 → 2605 过度交易
  Decay 关闭 → 趋势月过度入场
  双扫关闭 → 2605 质量崩 (-\)
  H1 ATR 延伸确认 → 容差过大
\\\

**诊断规则**: 一轮改动迭代 5 次仍不收敛 → 回到基线重新出发。

### 3.9 最小手数学约束

\\\
\ 账户 × 0.01 手 × XAUUSD = \.00/美元价格移动
84 笔/月 × WR=1.14 × avg_W=\.19 = +\
→ 要 +\ 需: 1600 笔/月 (不可能) 或: 同样 84 笔 × \.57/笔 (扩大 3 倍)

改进方向:
  \,500 账户: 0.03-0.05 手
  84 笔 × \-2/笔 → \-160
  方向锁质量保持 → \-500
\\\

### 3.10 双月验证放宽策略

当目标是最大化 2605 盈利时,接受 2505 损失:
\\\
new_golden_ratio = (2605_pnl + 2505_pnl) > bd07_2505_pnl
2605 必须盈利 \ 且 2505 退化不超过 \ (24%)
\\\

BD08 最优 (v10 方向锁 + DTP=2.0): 2605=\, 2505=\.5K。

---

## §4 关键诊断模式 (来自实战)

### 模式 A: 双扫拦截率在坏月激增 (~20%→57%)
→ 入口逻辑在震荡月仍产生大量信号,但双扫在正确拦截。改进: 加绕过双扫的新入口 (BOS Retest)。

### 模式 B: 月亏停止在坏月频繁触发
→ \ 账户仅 \ 亏损 = 2 笔连亏。改进方向: 入口质量,不是冷却时间。

### 模式 C: 单参数改动回测结果完全不变
→ 参数根本不是根因。必须引入新信号类型。

### 模式 D: H4 方向锁是单一最有效改进
→ BD07 (-\) → +H4 方向锁 (-\)。无需 detect chop/trend,只需拦截逆势入场。

### 模式 E: DTP 碎片化趋势利润 → 0.01 手锁死绝对利润
→ 2605: 84 笔全顺势但仅 +\。趋势波幅 \ 但 DTP@2.0R 切碎 90% 利润。
→ 0.01 手最小限制锁死 \$/笔。双重瓶颈: 出口机制 + 手数限制。

### 模式 F: 结构性级别持久化 → 多日回踩获利
→ 4580 案例: H4 swing 5/3 跌破 → BOS 信号 5/3 过期 → 但价格直到 5/15-30 才回踩。
→ MaxBars=720 (12h) 远不够。有效突破位应永不过期。

