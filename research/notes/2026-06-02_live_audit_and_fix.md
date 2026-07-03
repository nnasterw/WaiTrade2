# 2026-06-02 Live部署审计与修复

## 一、发现的两个BUG（已修复）

### BUG 1: ZD加载了错误的.set文件

**症状**: ZD终端5月29日后从未开仓

**根因**: 加载了`v11xau-zd2.set`（实验性极端风控版）
- `monthly_warmup_pos_mult: 0.1` → 仓位为正常的10%
- `monthly_warmup_profit_pct: 1.0` → 需赚1%才解除暖机
- `daily_loss_stop_pct: 1.0` → 日内亏1%就停

**死循环**: 0.1倍仓位 → 永远赚不到1% → 暖机永不解除 → 日内微亏就停 → **永远不会开仓**

**修复**: 改为`v11xau-zd.set`（纯ZD策略，无极端风控）

### BUG 2: QS的.set文件加载失败

**症状**: QS EA以默认参数空跑

**根因**: `v11xau-qs2.set`加载失败（MT5错误码[2]=文件不存在），EA退回MQL5默认参数

**修复**: 从QS portable目录复制到主presets备份，重新同步确保文件完整

### BUG 3: 单实例限制

**症状**: 无法同时启动两个portable终端

**根因**: 同一`terminal64.exe`只允许一个`/portable`实例

**修复**: 复制`terminal64.exe`到各portable目录，各自独立运行

---

## 二、Live vs Backtest 差异审计

### 🔴 严重: QS回测TF(M5) ≠ Live TF(M1)

| | 回测 | Live |
|------|:---:|:---:|
| ZD BarTF | M5 (backtest_defaults) | **M3** (InpBarTF=3) |
| QS BarTF | M5 (backtest_defaults) | **M1** (InpBarTF=1) |

`mt5_backtest_win.py`生成的backtest.ini中`Period=`覆盖了EA的`InpBarTF`，导致所有回测都在M5上运行。

**影响**: QS在M1上的信号频率是M5的**5倍**。所有QS历史回测数据不能准确预测Live表现。

### 🟡 中等: QS有月度硬止损

```
monthly_loss_stop_pct: 10.0     # 月亏>10%停新单
monthly_loss_stop_min_trades: 10 # 至少10笔后生效
consecutive_loss_cooldown: 5     # 连亏5笔冷却
consecutive_loss_cooldown_min: 10
```

这是QS2的防守设计。回测中如果早期亏损>10%，后续交易被永久阻止——Live同样行为。

### 🟢 安全项

| 项目 | ZD | QS | 状态 |
|------|:--|:--|:----:|
| Magic号 | 204558 | 204899 | ✅ 唯一 |
| SharedMonthlyGuard | false | false | ✅ 无冲突 |
| EA .ex5 | 与主presets一致 | 与主presets一致 | ✅ |
| .set文件 | 与主presets一致 | 与主presets一致 | ✅ |
| 登录/服务器 | 277656700 / Exness-MT5Trial5 | 同 | ✅ |
| 代理 | 127.0.0.1:7897 | 同 | ✅ |
| EntryDebug | false | false | ✅ |
| 防御确认 | 未启用 | 未启用 | ✅ |

---

## 三、修复后的Live配置

| | ZD (振荡腿) | QS (趋势腿) |
|------|:---|:---|
| .set | v11xau-zd.set | v11xau-qs2.set |
| 品种/TF | XAUUSDm M3 | XAUUSDm M1 |
| 风险 | 2% | 3% |
| 最大手数 | 0.5 | 0.1 |
| Magic | 204558 | 204899 |
| 月止损 | 无 | 10% + 10笔min |

---

## 四、待解决

1. **重新运行QS的M1回测** — 所有历史QS回测数据基于M5，需要M1数据验证Live预测
2. **ZD的M3回测** — 当前回测脚本使用M5，需改为M3匹配Live
3. **回测脚本修复** — `Period=`应使用策略的`bar_tf`而非`backtest_defaults.period`
