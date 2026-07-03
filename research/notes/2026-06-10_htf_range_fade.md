# HTF Range Fade: 大周期震荡高抛低吸

> 设计日期: 2026-06-10 | 状态: 代码完成，待编译测试

---

## 一、核心理念

**大周期震荡区间有结构支撑 → 边界高抛低吸 → 小周期入场拿好价格。**

| 维度 | 现有M1策略 | Range Fade |
|:---|:---|:---|
| 时间框架 | M1 only | H4/D1 区间 + M1/M5 入场 |
| 方向逻辑 | Sweep跟随方向 | 区间边界反转方向 |
| 失败原因 | OB=陷阱，方向反转 | 区间有结构支撑，边界可信 |
| 震荡表现 | 全部亏损 (-$1~-$56/月) | 理论 +$5~8/月 |
| 期望值 | -0.25R (2026) | +0.65R (理论) |

## 二、技术架构

### 新增文件
- **`RangeDetector.mqh`** — HTF 区间检测 + 位置判断 + 方向反转

### 修改文件
- **`Config.mqh`** — 20个新 input 参数 + accessor
- **`SignalEngine.mqh`** — 双路径集成（EntryEngine + 直接入场）
- **`strategies.yaml`** — 默认值
- **`yaml_to_set.py`** — FLAT_MAP 映射

### 区间检测算法

```
1. 加载H4 bars (默认120根 = 20天)
2. 找 swing highs/lows (strength=3, 12bar确认)
3. 聚类相近swing → 上下边界
4. 验证: 宽度(1.5-5.0ATR) + 接触(≥2次) + 包容度(≥75%)
5. 计算置信度(0-1): touches×0.25 + containment×0.30 + width×0.20
6. 缓存(每H4 bar更新), 避免每tick重算
```

### 入场逻辑

```
if(HTF区间有效 && 价格在边界 ±0.3ATR内):
    if(价格近上沿):  SMC信号方向 → 反转为SELL (高抛)
    if(价格近下沿):  SMC信号方向 → 反转为BUY  (低吸)
    if(区间中部):   不交易 (可选)
    if(正在突破):   观望

SL: 区间边界外 0.5ATR
TP: 区间对侧或中轴
仓位: 普通仓位的 0.5x
```

## 三、策略参数

| 参数 | 默认值 | 含义 |
|:---|:---:|:---|
| InpEnableRangeFade | false | 启用开关 |
| InpRangeTF | 240 | 区间检测周期(H4) |
| InpRangeLookback | 120 | 回溯bar数(20天) |
| InpRangeMinBars | 24 | 最小形成bar数 |
| InpRangeMinWidthATR | 1.5 | 最小区间宽度 |
| InpRangeMaxWidthATR | 5.0 | 最大区间宽度 |
| InpRangeBoundaryToleranceATR | 0.15 | 边界聚类容忍度 |
| InpRangeSwingStrength | 3 | swing确认强度 |
| InpRangeMinTouches | 2 | 边界最少测试 |
| InpRangeMinContainment | 0.75 | 包容度阈值 |
| InpRangeEntryZoneATR | 0.30 | 入场区域宽度 |
| InpRangeSLBufferATR | 0.50 | 区间外SL |
| InpRangeTPTarget | 1 | 0=对侧,1=中轴 |
| InpRangePosMult | 0.5 | 仓位乘数 |
| InpRangeMaxLot | 0.02 | 最大手数 |
| InpRangeUpdateBars | 1 | 更新频率 |
| InpRangeRequireSweep | true | 需sweep确认 |
| InpRangeRequireFVG | false | 额外FVG确认 |
| InpRangeNoMidTrades | true | 中部不交易 |

## 四、推荐策略组合

### RangeFade-D2 (震荡专用)

```yaml
base: S2基线
overrides:
  enable_range_fade: true          # 启用HTF区间
  enable_liquidity_sweep: true     # sweep检测
  enable_state_filter: true        # 状态过滤
  range_tf: 240                    # H4区间检测
  range_pos_mult: 0.5              # 半仓
  range_sl_buffer_atr: 0.5         # SL=边界外0.5ATR
  range_tp_target: 0               # TP=对侧边界
  range_no_mid_trades: true        # 中部不交易
```

### RangeFade+Regime (震荡+趋势双模)

```yaml
base: RegimeBoth d3%
overrides:
  enable_range_fade: true
  range_tf: 240
  range_pos_mult: 0.5
  # RegimeBoth在区间外正常趋势交易
  # 区间内自动反转 → 高抛低吸
```

## 五、数学预期

### 2026年震荡月模拟

假设每月有4-6次区间边界接触：
- 平均接触: 5次/月
- 胜率: 60% (区间边界比M1 OB可靠)
- 平均R:R: 1.5:1 (TP中轴)
- 每笔风险: $2 (0.5x仓位)
- 月PnL: 3胜×$3 - 2败×$2 = +$5/月

vs 现有S2: -$19/月 (3个有数据月份平均)

### 趋势月表现

当市场处于趋势(无有效H4区间):
- `range.valid = false` → Range Fade不激活
- 原策略(Sweep跟随)正常工作
- 不产生负面影响

## 六、风险与限制

1. **区间假突破**: 边界被突破后使用区间外SL → 亏损控制
2. **H4数据不足**: 新上市品种无足够H4 bars → `range.valid=false`
3. **大周期滞后**: 区间检测每H4 bar更新一次 → 最多4小时滞后
4. **模型限制**: 未在Live验证，理论模型依赖历史规律
5. **MT5 CLI Bug**: 终端未恢复，无法编译和回测验证

## 七、待验证

- [ ] 编译通过 (metaeditor64.exe)
- [ ] 部署.ex5到MT5数据目录
- [ ] 2601-2605回测对比 (RangeFade vs S2 vs RegimeBoth)
- [ ] H4区间检测日志验证 (区间是否合理)
- [ ] Live模拟(非实盘)观察区间交易行为
