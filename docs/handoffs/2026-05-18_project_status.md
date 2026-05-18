# Handoff: WaiTrade2 项目状态

**日期**: 2026-05-18
**仓库**: `git@github.com:nnasterw/WaiTrade2.git` (main @ 8170efb)
**工作目录**: `/Users/wen/Projects/ClaudeCode/WaiTrade2`

---

## 当前项目状态

### 定版策略（已验证盈利）

| 策略 | 品种 | TF | 验证 | 结果 |
|------|------|-----|------|------|
| **v99g1** | XAU+XAG+EUR | M5 | 180天 | $842(+321%) |
| **v99j1** | BTC+ETH | M30 | 365天 | $677(+238%) |
| **v99g2** | 贵金属(新) | M5 | 待验证 | DTP partial 50%落袋 |
| **v99j2** | BTC(新) | M30 | 待验证 | SL 2.0ATR |

### 最新远端改动 (8170efb)

另一会话做了以下重要改动：

1. **EA重命名**: `WaiTrade` → `WaiTrade2`（目录/Include/Print全部改）
2. **新策略**: v99g2（DTP首次50%落袋+余仓0.30回撤）+ v99j2（BTC SL2.0ATR）
3. **心跳日志**: 每小时HEARTBEAT存活日志(bar/ob/pos/atr/spread/state)
4. **DTP partial close**: ExitMode=1 首次回撤平50%，余仓继续
5. **阶梯DTP**: stage2/stage3 input预留，默认关闭
6. **mt5_live_runner**: profile名改为 `WaiTrade2_Live`，inputs 改 plain key=value
7. **Windows Live验证**: MT5 /config:[StartUp] 启动方式验证通过
8. **yaml_to_set**: 新增8个参数映射
9. **CLAUDE.md**: 更新 .chr 不支持EA说明、Model4铁律

### 关键架构认知

- **EA路径**: `mql5/Experts/WaiTrade2/WaiTrade_OB.mq5`（已从WaiTrade改名）
- **Include路径**: `mql5/Include/WaiTrade2/`
- **编译**: `python scripts/mt5_compile.py WaiTrade2/WaiTrade_OB`
- **Live Profile**: `WaiTrade2_Live`
- **Model 4 Real Ticks** 是唯一可信回测模式
- **品种独立参数**: 贵金属(M5/SL0.1ATR/BE1.0R) vs 加密(M30/SL1.5ATR/BE2.0R)

### 8-Gap 信号修复（内置于OBDetector）

1. OB用实体(open/close)不含影线
2. Displacement突破前3根高/低
3. 实体占比>=50%
4. 23:00-06:00不建OB
5. strength<0.5不入场
6. 动态TTL
7. risk>3×ATR不入场
8. 逆势+risk>1.5ATR不入场

### EntryEngine 状态机（v99核心）

触及OB → 等bounce(ob_height×bounce_pct) → offset guard → 入场

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `CLAUDE.md` | 项目完整指引 |
| `config/strategies.yaml` | 210+策略参数 |
| `strategy_versions/v9.9_final.md` | v99系列完整文档 |
| `docs/handoffs/2026-05-17_v99_strategy_evolution.md` | 20轮策略进化记录 |
| `docs/handoffs/2026-05-15_strategy_evolution.md` | 策略进化全景 |
| `mql5/Presets/V99g1.set` / `V99j1.set` | 定版preset |
| `research/notes/model4_full_comparison.md` | Model 4全策略对比 |

---

## 待完成

1. **v99g2/v99j2 回测验证** — 新策略未跑回测
2. **Live部署实测** — XAU+XAG+EUR(v99g1) + BTC+ETH(v99j1)
3. **Windows Live启动** — /config:[StartUp] 方式已验证
4. **更多品种** — GBPJPY(PF1.84样本少), USTEC(接近持平)
5. **strategy_versions补缺** — v9.7a/v9.7b/v9.8/v9.8a 文档未写

## 建议技能

- `/wf-improve-strategy` — 继续策略优化/v99g2验证
- `/diagnose` — Live运行/编译问题
