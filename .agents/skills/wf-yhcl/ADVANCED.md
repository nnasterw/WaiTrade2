# wf-yhcl v3.1 ADVANCED - 按需加载的高级模块

> 本文档存放主流程用不到的深入分析模块。仅在用户明确要求或 L3 触发对应模式时加载。
> 与 SKILL.md / REFERENCE.md 区别: SKILL.md = 主流程, REFERENCE.md = 可复用规律, ADVANCED.md = 高级分析代码。

---

## §AI AI 辅助搜索工作流

> 加载条件: 用户要求 ultrathink / 自动化假设生成。

### Step 1: 数据准备

```
python scripts\backtest_digest.py ^
  --report results/backtest/<strategy>.txt --export-csv
```

### Step 2: 特征挖掘

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("results/backtest/<strategy>.trades.csv")
df["win"] = (df["pnl_proxy"] > 0).astype(int)

features = ["bounce_ob", "confirm_pos", "entry_offset_r", "peak_r",
            "giveback_r", "signal_type", "bounce_sec", "dtp_peak_r"]
X = df[features].fillna(0)
y = df["win"]

model = RandomForestClassifier(n_estimators=200)
model.fit(X, y)
importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
print(importances)
```

### Step 3: 假设生成

```python
top_features = importances.head(20).index.tolist()
win_df = df[df["win"] == 1]
filter_rules = []
for f in top_features:
    threshold = win_df[f].quantile(0.25)
    filter_rules.append(f"{f} >= {threshold}")
# 例: bounce_ob > 0.30 AND confirm_pos > -0.5 AND entry_offset_r < 0.3
```

### Step 4-5: 回测验证 + WFYS 评分

```
python scripts\yaml_to_set.py <strategy> -o mql5/Presets/<strategy>.set
python scripts\mt5_backtest_win.py ^
  --strategy <strategy> --symbol BTCUSDm --from 2024.06.01 --to 2026.05.31 --model 4

python scripts\wfys_score.py ^
  --monthly-csv results/backtest/<strategy>_closetime_24m.csv ^
  --continuous-report results/backtest/<strategy>.txt ^
  --trades-csv results/backtest/<strategy>.trades.csv ^
  --spec btc
```

### Step 6: 迭代循环

```
若 WFYS < 80 或 周单数 < 2:
  -> 调整 filter_rules (放宽/收紧)
  -> 重新跑 Step 4-5
若达标:
  -> tick 折线图验证
  -> 多周期多品种验证 (跨 BTC/XAU/ETH)
  -> 固化策略 + 写入 wf-yhcl 已知有效规则库
```

---

## §Tick Tick 折线图可视化

> 加载条件: 需要可视化单笔交易时。

```python
import pandas as pd
import matplotlib.pyplot as plt
from mt5_tools import get_tick_data

df = pd.read_csv("results/backtest/<strategy>.trades.csv")
fig, axes = plt.subplots(len(df), 1, figsize=(14, 3 * len(df)))

for i, trade in df.iterrows():
    ax = axes[i]
    ticks = get_tick_data(symbol=trade["symbol"],
                          from_time=trade["time"] - pd.Timedelta(minutes=30),
                          to_time=trade["close_time"] + pd.Timedelta(minutes=10))
    ax.plot(ticks["time"], ticks["price"], color="gray", alpha=0.5)
    ax.axvline(trade["time"], color="blue", linestyle="--", alpha=0.5)
    ax.scatter(trade["time"], trade["entry"], color="blue", s=50, marker="^")
    color = "green" if trade["pnl_proxy"] > 0 else "red"
    ax.scatter(trade["close_time"], trade["exit"], color=color, s=80, marker="v")
    if trade["bounce_ob"]:
        ax.axhspan(trade["entry"] * 0.999, trade["entry"] * 1.001, alpha=0.2, color="orange")
    ax.set_title(f"Trade {i}: {trade[chr(34)+chr(100)+chr(105)+chr(114)+chr(34)]} R={trade[chr(34)+chr(114)+chr(34)]}:")

plt.tight_layout()
plt.savefig("results/diagnose/tick_chart_<strategy>.png", dpi=150)
```

### 用途

1. 视觉识别盈利单 vs 亏损单 的入场 K 线形态差异
2. 找出看似相同但结果相反的成对交易
3. 验证 pinbar / 突破 / 多周期信号的实际效果
4. 辅助假设生成: tick-level 价格结构特征

---

## §WFYS WFYS 评估标准扩展

> 加载条件: 评估 v3 维度 (趋势结构/订单流质量)。

### 现有 4 模块 / 100 分

```
[稳定性] /30: 24 月盈利月数、亏损月数量、利润集中度
[利润能力] /30: 24 月总收益、720d 净利、强利润月/大趋势月
[风险质量] /25: 720d 回撤、Recovery Factor、Profit Factor、Sharpe/Sortino/Calmar
[趋势利润结构] /15: avg_W/|avg_L|、>3R 大赢单占比、<0.5R 微利单占比
```

### v3.0 扩展 (3 个可选模块)

```
[趋势结构] /15 (NEW)
  |- pinbar 信号命中率 /5
  |- 多周期同频命中率 /5
  |- 微观结构质量 (bounce_ob + confirm_pos) /5

[订单流质量] /10 (NEW)
  |- sweep 入场盈利率 /4
  |- FVG 入场盈利率 /3
  |- BOS 入场盈利率 /3

[结构胜率分布] (NEW, 非评分, 输出报告)
  |- 盈利单 K 线形态直方图
  |- 盈利单市场结构分布 (顺/逆/区间)
  |- 多周期一致性 vs 持仓时长散点图
```

### v3.0 评估铁律

```
硬门槛 (hard_gates):
  + 必须通过 v3.0 五维度诊断 (至少 1 个维度命中率高)
  + 必须有至少 1 个结构性 (非时间) 过滤规则
  + 必须经过 AI 辅助搜索验证循环
  + 严禁含 hour/day/month 后视镜过滤
```

---

## §Phase 0 过滤栈逐层拆解

> 加载条件: 需要诊断策略的过滤栈有效性。

### 0.1 提取过滤器列表

```yaml
过滤器栈 (从 BD07 .set 反编译):
1. PassDoubleSweepConfirm       # 双扫确认(20bar窗口双方向LP)
2. InpMonthlyLossStopPct=3.0    # 月内亏损停止($6)
3. InpEnableTickNoiseGate       # Tick噪音门控(方向一致率<20%)
4. InpEnableHTFNetPushFilter    # H1净推进过滤
5. IsInCooldown                 # 全局冷却
6. PassOBReentryCooldown        # OB重入冷却
7. InpEntryBlockCounterStrong   # 强逆势拦截
8. InpEnableDecayExit           # 衰减出口(weakExit/MinR)
9. InpEnableStateFilter         # 市场状态过滤
10. InpEnableScoring            # OB评分过滤
```

### 0.2 逐层估算拦截率

```
过滤器    | 好月拦截率 | 坏月拦截率 | 说明
---------|----------|----------|------
双扫确认 | ~20%     | ~57%     | 窄幅震荡: LP双方向被扫频率低
月亏停止 | ~0%      | ~30%     | $200账户: $6=2笔连亏触发
Tick噪音 | ~8%      | ~15%     | 震荡Tick方向混乱
HTF净推  | ~5%      | ~10%     | H1方向频繁变化
```

---

## §五维度 五维度诊断详细 EA 参数

> 加载条件: 需要为五维度诊断配置 EA 参数。

### 维度 1: K 线形态 (Candlestick Patterns)

入场形态: pinbar / engulfing / inside bar / hammer

EA 参数:
- InpEnablePinbarEntry: bool
- InpPinbarWickPct: float (默认 0.6)
- InpEngulfBodyPct: float (默认 0.7)
- InpPinbarMinBounce: float

### 维度 2: 价格结构 (Price Structure)

EA 参数:
- InpEnableBOS: bool
- InpEnableCHoCH: bool
- InpBOSATRMult: float
- InpSwingPivotBars: int

### 维度 3: 多周期共振 (Multi-Timeframe Confluence)

EA 参数:
- InpEnableHTFNetPushFilter: bool
- InpHTFNetPushBars: int
- InpHTFNetPushThreshold: float
- InpH1AlignmentRequired: bool

### 维度 4: 订单流信号质量 (Order Flow Signal Quality)

EA 参数:
- InpEnableLiquiditySweep: bool
- InpEnableFVG: bool
- InpEnableMicroBOS: bool
- InpEnableMitigationEntry: bool
- InpEnableDoubleSweepConfirm: bool
- InpMinOBSpreadMult: float
- InpBouncePct: float

### 维度 5: 微观结构评分 (Micro-Structure Score)

```python
micro_score = bounce_ob * 0.3 + (confirm_pos + 1) * 0.2
              + (1 - abs(entry_offset_r)) * 0.2 + (peak_r / 5.0) * 0.3
```

EA 参数:
- InpMinOBSpread: float
- InpBouncePct: float (默认 0.25)
- InpEntryDepthPct: float (默认 0.67)
- InpMinOBStrength: float (默认 0.5)

