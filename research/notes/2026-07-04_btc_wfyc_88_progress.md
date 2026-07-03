# BTC WFYS 88 攻关 — 阶段性记录 (2026-07-04)

## 目标
改进 BTC EA 策略，使 WFYS 评分达到 88+。

## 基线
- **v11-btc1-trend68** (2026-07-04): WFYS 79.10 分，等级 淘汰
- **v11-btc1-qual232** (2026-07-01): WFYS 80.17 分，等级 观察级候选
- 24 月回测 (2024.06 ~ 2026.05, 729 天, M5, 资金 $200, Model 4)
- 108 笔交易，42.6% 胜率，PF 2.04，最终余额 $9870

## 主要拖累
1. **24月盈利月数** 20/24（需 21+）→ -1.67 分
2. **亏损月数量** 4（需 ≤3）→ -4 分
3. **>3R大赢单占比** 21.1%（目标 50%）→ -3.47 分

## 亏损月分布
- 2024-11: -$53.86 (3 笔, 1 SL 击穿 @ 6.2min, bounce_ob 0.253)
- 2025-01: -$118.25 (5 笔, 2 SL 击穿 @ 8.9/9.4 min, bounce_ob 0.252/0.256)
- 2025-10: -$9.82 (6 笔, 2 SL 击穿 @ 2.85/15.1 min, bounce_ob 0.262/0.321)
- 2026-05: -$160.93 (3 笔, 2 SL 击穿 @ 9.6/24.8 min, bounce_ob 0.251/0.290)

## 第一轮实验 (trend74-78): 单 lever 改动
- trend74 (VSL only, 2 bars): **68.58** (-10.5)  ← VSL 杀大赢单
- trend75 (SL buffer 2.0 + VSL 2): **46.53** (-32.5) ← 灾难组合
- trend76 (btc_min_score=5): **79.10** (=) ← 已被其他逻辑过滤
- trend77 (min_ob_strength 0.6): **79.10** (=) ← 同上
- trend78 (Trail1/2/3): **79.10** (=) ← **关键发现：HTFSkipTrail=true 屏蔽 Trail**

## 关键发现
**InpHTFSkipTrail=true + InpHTFSkipDTP=true**（BTC profile 默认）
- BTC 走 HTF 目标模式（InpHTFMeasuredMoveR=4.0）
- 跳过全局 Trail/DTP
- 改 InpTrail* / InpDTP* 无效

## 第二轮实验 (trend79-82): Trail/DTP 改动（基本无效）
- trend79 (3-level Trail): **79.10** (=) ← HTFSkip 屏蔽
- trend80 (DTP Stage 2/3 + PostPartial): **75.60** (-3.5) ← 产生大亏月
- trend81 (DTP + Trail): **75.60** (= trend80)
- trend82 (单 Trail1 2.0/0.5): **79.07** (=)

## 下一轮方向 (trend83+)
需绕过 HTFSkip 机制:
1. **HTFDTP 激活**: HTFSkipDTP=false, HTFDTPTriggerR=1.5, HTFDTPRetrace=0.3
2. **HTF 目标降低**: HTFMeasuredMoveR 4.0→3.5, HTFMinTargetR 3.0→2.5
3. **窄范围 bad_bounce**: 0.25-0.30 + mult 0.4（针对 0.262 噪声 SL）
4. **精细化小时过滤**: 阻断 h=9-10 高损时段

## 已生成文件
- config/strategies.yaml: 新增 trend74-82 (5+5 = 10 个策略)
- mql5/Presets/v11-btc1-trend7{4,5,6,7,8,9}.set
- mql5/Presets/v11-btc1-trend8{0,1,2}.set
- results/backtest/v11-btc1-trend7{4,5,6,7,8,9}_*.{txt,md,trades.csv,wfys_*.json}
- results/backtest/v11-btc1-trend8{0,1,2}_*.{txt,md,trades.csv,wfys_*.json}
