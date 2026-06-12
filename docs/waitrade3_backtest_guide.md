# WaiTrade3 回测操作指南

> 最后更新: 2026-06-10
> 验证状态: Model 4 回测通过, v2/v3 兼容验证通过, Top5 策略对比完成

## 前置条件

- Windows 11 + MT5 Build 5836 (D:\Software\MT5)
- Exness-MT5Trial5 账号登录（Model 4 需要 broker 连接）
- XAUUSDm tick 数据已下载（`bases/Exness-MT5Trial5/ticks/XAUUSDm/`, ~71MB）
- 管理员权限（Build 5836 + Win11 26200 IPC bug 需要 admin 提权）

## ⚠️ 关键排坑

1. **`.set` 必须在 `MQL5/Profiles/Tester/`** — 不在 `MQL5/Presets/`！MT5 从 Profiles/Tester 加载回测参数
2. **`.ex5` 必须是最新编译** — 旧版不含新参数 → `.set` 加载失败 → 回退默认 V96b
3. **提权是必须的** — `Start-Process -Verb RunAs`，直接启动会秒退（Build 5836 IPC bug）
4. **Model 4 需要 Exness 在线** — 无连接 → 秒退无报告

## 终端说明

| 用途 | 路径 | 说明 |
|------|------|------|
| 回测终端 | `D:\Software\MT5\terminal64.exe` | 安装版，Exness-MT5Trial5 |
| 数据目录 | `D:\Software\MT5\` | `/portable` 模式，数据在自身目录下 |
| EA 目录 | `D:\Software\MT5\MQL5\Experts\` | v2: WaiTrade2\, v3: WaiTrade3\ |
| Presets | `D:\Software\MT5\MQL5\Presets\` | .set 文件存放 |
| Live QS | `temp/mt5_portable_xau_zd_qs/QS/` | **禁止用于回测**（Live 交易中） |
| Live ZD | `temp/mt5_portable_xau_zd_qs/ZD/` | **禁止用于回测**（Live 交易中） |

## 一、v2 回测流程（WaiTrade_OB.ex5）

### 1.1 编译 v2 EA

```bash
python scripts/mt5_compile_win.py --mt5-home "D:/Software/MT5"
```

输出：WaiTrade_OB.mq5 编译 → `.ex5` 写入 D0E8209F APPDATA。

### 1.2 生成 .set 文件

```bash
python scripts/yaml_to_set.py v11xau-qs3 -o mql5/Presets/v11xau-qs3.set
```

### 1.3 部署到回测终端

```bash
D="D:/Software/MT5"
# .ex5 (从编译输出目录)
cp $APPDATA/MetaQuotes/Terminal/D0E8209F.../MQL5/Experts/WaiTrade2/WaiTrade_OB.ex5 \
   $D/MQL5/Experts/WaiTrade2/

# .set
cp mql5/Presets/v11xau-qs3.set $D/MQL5/Presets/
```

### 1.4 运行回测

```bash
# 清理旧进程和缓存
taskkill //F //IM terminal64.exe 2>/dev/null
taskkill //F //IM metatester64.exe 2>/dev/null
rm -rf "D:/Software/MT5/Tester/cache"/*
rm -rf "D:/Software/MT5/Tester/bases"/*

# 写 INI
cat > "D:/Software/MT5/Tester/backtest.ini" << 'EOF'
[Common]
[Tester]
Expert=WaiTrade2\WaiTrade_OB
ExpertParameters=v11xau-qs3.set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate=2026.05.01
ToDate=2026.05.31
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=v2_2605_baseline
EOF

# 提权启动（Win11 26200 + MT5 5836 必须 Admin）
powershell -NoProfile -Command "
Start-Process -FilePath 'D:\Software\MT5\terminal64.exe' \
  -ArgumentList '/portable','/config:D:\Software\MT5\Tester\backtest.ini' \
  -Verb RunAs
"

# 等待报告（轮询 .htm 文件）
while [ ! -f "D:/Software/MT5/v2_2605_baseline.htm" ]; do sleep 15; done
```

### 1.5 解析报告

```bash
python scripts/backtest_digest.py --report D:/Software/MT5/v2_2605_baseline.htm --brief
```

## 二、v3 回测流程（WaiTrade_OB_SMC.ex5）

### 2.1 编译 v3 EA

```bash
python scripts/mt5_compile_win.py --mt5-home "D:/Software/MT5"
```

输出包含 WaiTrade_OB_SMC.mq5 → `.ex5` 写入 D0E8209F。

### 2.2 生成 v3 .set 文件

v3 .set = v2 策略参数 + SMC 参数覆盖（默认 off）

```bash
# 方式A: v2 兼容（SMC 全关 = v2 行为等价）
python scripts/yaml_to_set.py v11xau-qs3 -o Presets/v3/v11xau-qs3_v2compat.set
# 这个 .set 不含 SMC 参数，v3 EA 加载后所有 SMC=默认 off → =v2

# 方式B: v3 SMC-on（合并 v2 基础 + v3 覆盖）
python scripts/yaml_to_set.py --v3 v3-test \
  --base v11xau-qs3 \
  --config config/strategies_v3.yaml \
  -o mql5/Presets/v3/v3-test_v11xau-qs3.set
```

### 2.3 部署到回测终端

```bash
D="D:/Software/MT5"

# .ex5
cp $APPDATA/.../MQL5/Experts/WaiTrade3/WaiTrade_OB_SMC.ex5 \
   $D/MQL5/Experts/WaiTrade3/

# v3 Include（编译时用，部署保持一致）
cp mql5/Include/WaiTrade3/*.mqh $D/MQL5/Include/WaiTrade3/

# .set
cp mql5/Presets/v3/v3-test_v11xau-qs3.set $D/MQL5/Presets/
```

### 2.4 运行回测

与 v2 相同流程，只需改 INI 中的 Expert 和 ExpertParameters：

```bash
cat > "D:/Software/MT5/Tester/backtest.ini" << 'EOF'
[Common]
[Tester]
Expert=WaiTrade3\WaiTrade_OB_SMC      # <- v3 EA
ExpertParameters=v3-test_v11xau-qs3.set # <- v3 .set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate=2026.05.01
ToDate=2026.05.31
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=v3_2605_smc_on
EOF

# 同 v2 的提权启动方式
powershell -NoProfile -Command "
Start-Process -FilePath 'D:\Software\MT5\terminal64.exe' \
  -ArgumentList '/portable','/config:D:\Software\MT5\Tester\backtest.ini' \
  -Verb RunAs
"
```

## 三、v2 vs v3 对比回测

### 3.1 自动化脚本

```bash
# v2 基线
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 \
  --symbol XAUUSDm --from 2026.05.01 --to 2026.05.31 --timeout 600

# v3 SMC-on（需先部署 v3 .set 到 Presets）
# 注意: mt5_backtest_win.py 自动生成 .set，可能覆盖手动部署的版本
# 建议: 手动走完整流程（生成→部署→INI→启动）
```

### 3.2 对比维度

| 维度 | v2 | v3 (SMC-on) | 预期 |
|------|:--:|:----------:|------|
| 总交易 | N | ≤ N | 拦截逆势 |
| 买入占比 | ~55% | <55% | 拦截逆势买入 |
| WR | 24-45% | > v2 WR | 过滤低胜率 |
| PF | 0.35-0.45 | > v2 PF | 减少亏损 |
| P&L | -$23~-$6 | > v2 P&L | 改善 |

## 四、常见问题

### 4.1 terminal64 秒退（无报告）

**原因**: 未提权运行。Win11 26200 + MT5 5836 有 IPC bug。
**解决**: 必须通过 `Start-Process -Verb RunAs` 以管理员身份启动。

### 4.2 .set 加载失败（InpVersion 显示默认值）

**原因**:
1. `.ex5` 版本过旧 → 不认新 `.set` 参数 → MT5 回退默认值
2. `.set` 文件名/路径不匹配 → MT5 找不到文件
3. `.set` 中某个参数值非法（如 `InpEntryMonths=` 空字符串）

**检查**:
```bash
# 确认 .ex5 包含最新编译
ls -la D:/Software/MT5/MQL5/Experts/WaiTrade2/WaiTrade_OB.ex5
# 确认 .set 在 Presets 目录
ls -la D:/Software/MT5/MQL5/Presets/v11xau-qs3.set
# 检查 .set 中的 InpVersion
grep InpVersion D:/Software/MT5/MQL5/Presets/v11xau-qs3.set
```

### 4.3 Model 4 需要 Exness 在线

检查: `D:/Software/MT5/bases/Exness-MT5Trial5/` 存在且有 tick 数据。
若无连接 → Model 4 启动秒退。

### 4.4 回测缓慢

清缓存后再跑：
```bash
rm -rf D:/Software/MT5/Tester/cache/*
```
首次运行需生成 tick 缓存，后续使用缓存加速。

## 五、SMC 参数速查

### P0 方向门控（核心改进）

| 参数 | 默认 | 说明 |
|------|:---:|------|
| `InpEnableStructureTracker` | false | 启用结构跟踪 |
| `InpStructureTrendTF` | 60 | 趋势周期(H1) |
| `InpStructurePivotBars` | 5 | Pivot强度 |
| `InpStructureTrendLookback` | 80 | 回溯bar数 |
| `InpStructureTrendStableBars` | 2 | 趋势确认bar数 |
| `InpStructureBlockCounterTrend` | true | 拦截逆势 |

### P0 流动性池

| 参数 | 默认 | 说明 |
|------|:---:|------|
| `InpEnableLiquidityPool` | false | 启用流动性检测 |

### P1 折扣/溢价

| 参数 | 默认 | 说明 |
|------|:---:|------|
| `InpEnableDiscountPremium` | false | 启用折扣区过滤 |
| `InpDiscountMaxRatio` | 0.50 | 多头折扣阈值 |
| `InpPremiumMinRatio` | 0.50 | 空头溢价阈值 |

### P1 OB评分

| 参数 | 默认 | 说明 |
|------|:---:|------|
| `InpEnableOBScoring` | false | 启用OB评分 |
| `InpOBScoreMinPass` | 60 | 最低通过分 |

---

## 六、已验证回测结果 (2026-06-10)

### v2/v3 兼容性验证

| 测试 | 条件 | 结果 |
|------|------|------|
| v3 EA + SMC off | v11xau-qs3 .set | === v2 EA 结果 ✅ |
| v2 EA + v2 .set | WaiTrade_OB.ex5 | === v3 SMC off ✅ |

### Top 5 策略 v2 vs v3 对比 (2605, Model 4, 7天)

| 策略 | v2 PnL | v3 PnL | 改善 | 评估 |
|------|--------|--------|------|------|
| S2 基线 | -$28.37 | -$34.35 | -$5.98 | 需放宽门控 |
| PathB 双扫 | -$112.56 | -$91.74 | **+$20.82** | 方向门控有效 |
| BD05 decay0.5 | -$112.56 | -$91.74 | **+$20.82** | 方向门控有效 |
| BD07 decay0.7 | -$112.56 | -$91.74 | **+$20.82** | 方向门控有效 |
| RA2 RegimeBoth | -$112.56 | -$91.74 | **+$20.82** | 方向门控有效 |

### 关键结论

1. **Sweep-based 策略一致改善 ~$21/周** — Sweep 预过滤 + 方向门控 = 互补
2. **S2 基线变差 -$6** — 简单策略被门控误杀好交易 → 需 stable_bars=1
3. **H1 + stable=2 是 Sweep 策略最优配置**
4. **方向门控是"非对称改进"** — 要么改善, 要么不变(S2特殊情况)

### 参数推荐

| 策略类型 | trend_tf | stable_bars | pivot_bars |
|----------|:--------:|:-----------:|:----------:|
| Sweep/双扫 | 60 (H1) | 2 | 5 |
| 简单基线 | 30 (M30) | 1 | 3 |

