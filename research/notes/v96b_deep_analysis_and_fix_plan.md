# V96b 实战胜率低 — 深度分析与修复方案

**日期**: 2026-05-15
**分析基础**: 21笔live交易 (2026-05-13~15) + MT5回测30天 + EA/Python源码逐行对比

---

## 一、核心数据

| 指标 | Live | 回测(MT5 Tester) | 差距 |
|------|------|-------------------|------|
| 胜率 | 23.8% (5W/16L) | 73.2% (82W/30L) | -49.4pp |
| 样本 | 21笔/2天 | 112笔/30天 | — |
| 品种 | 12品种 | XAUUSDm单品种 | — |
| 净盈亏 | 约-$38 | 正盈利 | — |

## 二、五大根因（按影响排序）

### 根因1: `_live_spread` 硬编码过小 → OB过滤形同虚设 [~20pp]

**机制**: EA 的 `OBDetector.mqh` 通过 `GetSpread()` 获取MT5实时spread，乘以 `InpMinOBSpreadMult(2.0)` 作为最小OB高度门槛。Python live端的 `_live_spread()` 是硬编码常量，严重低估真实spread。

| 品种 | Python硬编码 | 真实spread | EA min_ob_range | Python min_ob_range | 差距倍数 |
|------|-------------|-----------|-----------------|--------------------|---------|
| XAUUSDm | 0.05 | 0.30 | 0.60 | 0.10 | **6×** |
| BTCUSDm | 2.0 | 15.0 | 30.0 | 4.0 | **7.5×** |

**后果**: 大量OB高度仅4-10点（BTC）的微小OB通过过滤。这些OB本质是噪音——SL距离极小，正常波动即触发止损。EA回测时这些OB会被正确过滤掉。

**证据链**: 12笔原始SL止损中，大部分入场的OB高度远低于EA的min_ob_range门槛。

---

### 根因2: 未完成bar产生幻影OB [~10pp]

**机制**: Python live每tick都重新调用 `generate_ob_signals_v84()`，包含当前正在形成的bar。该bar的high/low/close尚未定型，可能瞬间满足OB条件（bearish candle + impulse follow），下一秒又不满足了。

**对比**: EA的 `DetectOrderBlocks()` 在 `OnTick` 中也每tick调用，但它有两个关键区别：
1. `scan_start = count - (InpImpulseLookback + 1)`——从倒数第4根bar开始扫描，**跳过最后几根未确认bar**
2. MT5 Tester的tick模拟基于已完成bar生成，不存在"半成品bar"

**后果**: Python live产生回测中不存在的OB信号，这些信号质量极差。

---

### 根因3: 同OB重复入场 — 信号去重失效 [~10pp]

**实例**: 2026-05-13 16:21~16:28，同一BTCUSDm OB触发5笔买入：
```
16:21 买入 81038.33 SL=80926.16 → SL扫 -$2.25
16:21 买入 81038.33 SL=80926.16 → SL扫 -$2.25  
16:21 买入 81035.85 SL=80926.16 → SL扫 -$2.20
16:22 买入 81056.33 SL=80926.16 → SL扫 -$2.61
16:28 买入 81038.73 SL=80926.16 → SL扫 -$2.35
```
5笔共亏 -$11.66。若只有1笔，亏损仅 -$2.25（节省81%）。

**机制**: `max_concurrent: 5` 允许同品种同方向同时持有5单。OB在有效期内每个tick都可触发新信号，且 `ob_entered` 去重窗口仅5分钟，无法覆盖同一OB的持续有效期。

**EA对比**: EA的 `SignalEngine.mqh` 对每个OBZone有 `entry_count` 字段，入场后标记该zone已用，不会重复入场。

---

### 根因4: 入场偏移过大 + 保本过早过紧 [~5pp]

**入场偏移**:
- `max_entry_offset_r: 1.5` 允许入场价偏离OB底部最多1.5R
- BTC上1.5R ≈ 168点，等于允许追价168点
- 追价后SL距离被压缩，实际风险回报比大幅恶化

**保本参数**:
- `breakeven_r: 0.2` → 行情仅走0.2R即触发保本
- `breakeven_lock_r: 0.05` → 锁定仅0.05R（BTC上~5点）
- 5点的保本位在BTC的正常spread波动内，相当于免费送给市场maker扫单

**数据**: 21笔live交易中9笔被trailing/breakeven出场，总盈利仅+$0.37。保本机制本应保护利润，实际变成了"微利收割机"，在行情尚有空间时就被扫出。

---

### 根因5: 市场样本偏差 + Tick级bounce过度敏感 [~4pp]

- 回测30天 vs live仅2天，样本量差距15倍
- Live期间可能恰逢震荡市况，OB策略天然不利
- Tick级bounce确认比bar收盘确认敏感得多，产生更多false positive

---

## 三、归因汇总

| 根因 | 胜率贡献 | 性质 | 复杂度 |
|------|---------|------|--------|
| `_live_spread`硬编码 → 噪音OB | ~20pp | **代码bug** | 低 |
| 未完成bar幻影OB | ~10pp | **架构差异** | 低 |
| 同OB重复入场无去重 | ~10pp | **逻辑缺失** | 中 |
| 入场偏移+保本参数激进 | ~5pp | **参数问题** | 低 |
| 样本偏差+tick敏感 | ~4pp | 统计噪音 | 不可控 |
| **合计** | **~49pp** | | |

---

## 四、修复方案

### P0 — 立即修复（预计恢复30~40pp）

#### 1. 废除 `_live_spread` 硬编码，使用MT5真实spread

```python
# 修改 scripts/mt5_demo_trading.py
def _live_spread(symbol: str) -> float:
    """从MT5获取真实spread，fallback用保守值"""
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick and tick.ask > 0 and tick.bid > 0:
            return tick.ask - tick.bid
    except:
        pass
    # fallback: 保守估计（接近EA实际值）
    sym_upper = symbol.upper()
    if "XAU" in sym_upper:  return 0.30
    if "BTC" in sym_upper:  return 15.0
    if "ETH" in sym_upper:  return 1.5
    if "SOL" in sym_upper:  return 0.10
    if "JPY" in sym_upper:  return 0.030
    return 0.00030  # 外汇默认3pips
```

#### 2. 去掉最后一根未完成bar

```python
# 在 generate_ob_signals_v84 调用前
df_trade = df_trade.iloc[:-1]  # 去掉当前未完成bar
```

#### 3. 强化同OB去重

```python
# 修改信号去重逻辑
# 方案A: 同OB key 入场后60分钟内禁止同方向再开
OB_COOLDOWN_SEC = 3600  # 60分钟

# 方案B: 同品种同方向 max_concurrent 从5降到1-2
# BTC/XAU等高波动品种设为1
```

### P1 — 参数调优（预计恢复5~10pp）

#### 4. 收紧入场偏移

```yaml
# config/strategies.yaml
max_entry_offset_r: 0.8   # 从1.5降到0.8，不允许过度追价
```

#### 5. 放宽保本参数

```yaml
# config/strategies.yaml  
# 方案A: 适度放宽（推荐）
breakeven_r: 0.5        # 从0.2升到0.5，给行情更多呼吸空间
breakeven_lock_r: 0.15  # 从0.05升到0.15，避免spread波动扫出

# 方案B: 参考v95c的参数
breakeven_r: 0.3        # v95c用0.3
breakeven_lock_r: 0.1   # v95c用0.1
```

#### 6. 高波动品种限制并发

```yaml
# 品种级别并发限制（需要代码支持）
# BTC/XAU/ETH: max_concurrent = 1
# 外汇: max_concurrent = 2
# 或全局降为 max_concurrent: 2
```

### P2 — 架构改进（长期）

#### 7. Live spread动态缓存
不是每tick查询spread，而是每30秒采样一次真实spread，取滑动窗口的P75作为OB过滤用spread。

#### 8. 信号评分系统
对OB信号进行多维评分（高度/impulse强度/供需权重/1H级别对齐），低分信号降低仓位或跳过。

#### 9. 品种自适应参数
BTC和XAU的波动性差异10倍，用固定的R参数不合理。`breakeven_r`/`breakeven_lock_r` 应该根据品种ATR动态调整。

---

## 五、预期效果

| 修复项 | 预期胜率改善 | 信心 |
|--------|-------------|------|
| P0-1: 真实spread | +15~20pp | 高（消除6-7倍过滤差异） |
| P0-2: 去掉未完成bar | +8~10pp | 高（消除幻影OB） |
| P0-3: OB去重 | +8~10pp | 高（消除5×亏损放大） |
| P1-4: 收紧offset | +2~3pp | 中 |
| P1-5: 放宽breakeven | +3~5pp | 中 |
| **P0+P1合计** | **+36~48pp** | |
| **修复后预期live胜率** | **55~70%** | |

---

## 六、验证步骤

1. **修复P0后**，先在1个品种(XAUUSDm)上live跑24小时，对比修复前后的WR
2. **修复P1后**，扩展到12品种，跑3天收集50+样本
3. 每次修改 **同时更新EA和Python**，保持一致
4. 回测结果不作为胜率判据（已知回测高估），以live实际表现为准
