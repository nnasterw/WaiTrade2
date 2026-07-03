# WaiTrade3 完整改进架构 — 2026-06-11

## 一、多周期协同体系

```
层级          | 模块           | 职责              | 状态
H4 趋势       | StructureTracker| 趋势方向(BULL/BEAR/CHOP)| ✅
H4/H1 Swing  | StructureTracker| BOS/CHOCH检测     | ✅
H4/H1 Swing→OB| MultiTFOB      | HTF入场区+宽SL    | ✅
H1 趋势门控   | RegisterChannel | P1: 禁逆势入场    | ✅
H4 自适应     | H4Adaptive     | 趋势宽/震荡严重入 | ✅
M1 OB        | OBDetector(v2) | 精确入场时机       | ✅
M1 EntryEngine| EntryEngine(v2)| 入场确认+执行      | ✅
BOS Retest   | BOSEntry       | 突破→回踩→入场    | 🆕
OB Freshness | (待实现)        | 反复缓解OB→跳过   | 📋
```

## 二、盈利模式矩阵

| 市场状态 | 主导模式 | 模块 | 例子 |
|------|------|------|------|
| H4趋势(BULL/BEAR) | MTF OB反弹 | MultiTFOB | 2505 Buy@支撑 |
| H4趋势 | BOS回踩 | BOSEntry | 突破→回踩→延续 |
| H4震荡(CHOP) | M1 Scalper | OBDetector(v2) | 快进快出微利 |
| H4震荡→突破 | BOS追单 | BOSEntry | 4580下破→回踩做空 |

## 三、4580 OB 盈利路径分析

```
H4 Swing High @4580 → 形成Sell OB:
  ├─ Touch 1: M1确认→做空→+$59   ← MTF OB反弹 (已有)
  ├─ Touch 2+: OB缓解→停交易     ← OB Freshness (待实现)
  ├─ Breakdown→回踩4580→做空+$53 ← BOS Retest (新实现)
  └─ 继续暴跌→底部Buy +$68       ← MTF OB反弹 (已有)
```

## 四、已实施改进

### P1: H4趋势强制对齐
- H4=BULL → 禁Sell; H4=BEAR → 禁Buy
- 2605 6d: $39→$103 (+163%)
- 代码: `InpMTFBlockCounterTrend`

### P2: 延长持仓时限
- TimeExitBars 40→120
- 2505 30d: $1,847→$2,610 (+41%)
- 在趋势市场让交易有足够时间发展

### MTF多周期OB加权
- H4/H1 swing points → OB zones
- TF权重×该TF的ATR做SL
- 2505 30d: $659→$1,847 (v2→v3-mtf)

## 五、已证伪改进

| 改进 | 失败原因 |
|------|------|
| P0 全部OB边缘入场 | 交易数-50%, 2505-$2,360 |
| H1 ATR SL替代M1 | 破坏scalper边缘, WR崩 |
| 关闭BE/TimeExit | WR→5%, 负期望 |
| OB评分过滤 | Bug修复后证实无益 |
| OB新鲜度过滤v1 | zone重建导致计数丢失 |
| 逆向拦截MTF | 2505 -70% |

## 六、待实施

| 优先级 | 改进 | 预期 | 难点 |
|:---:|------|------|------|
| P0 | OB Freshness v2 | 避4580式绞肉 | 跨bar持久化追踪 |
| P1 | 动态BOS Retest权重 | 提高BOS信号精度 | H4 vs H1 BOS选择 |
| P2 | FVG趋势跟随 | 新信号类型 | 全新模块 |

## 七、最终参数 (v3-mtf)

```yaml
sl_buffer_atr: 0.6          # M1 scalper SL
time_exit_bars: 120         # 延长持仓
breakeven_r: 0.6            # BE触发
breakeven_lock_r: 0.8       # BE锁定
enable_h4_adaptive: true    # H4自适应重入
mtf_block_counter_trend: true  # P1趋势对齐
h4_chop_max_entries_per_ob: 1  # 收紧CHOP
h4_chop_reentry_cooldown_min: 60
h4_chop_cooldown_bars: 5
mtf_ob_sl_buffer_atr: 0.5   # MTF SL
mtf_max_weight: 3.0          # 权重上限
bos_retest_entry: true       # BOS回踩入场
```
