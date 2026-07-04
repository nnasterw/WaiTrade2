# BTC 策略 WFYS 攻关 Context

> 2026-07-04 创立。封装本轮 BTC 策略 WFYS 评分达 93+ 攻关中确立的领域词汇。
> 词汇表不含实现细节, 仅定义术语。代码细节在 research/notes/ 下, 实现决策在 ADRs 下。

## Language

**WFYS (Win-First-Your-Self):**
统一的策略验收评分系统, 综合稳定性 / 利润能力 / 风险质量 / 趋势利润结构四个模块, 总分 100。
_Avoid_: 综合评分, 总分, 回测评分

**WFYS Hard Gates (硬门槛):**
WFYS 的 18 个二值门槛 (24月盈利月数, 亏损月数量, 大亏月, Top3/5 集中度, 720d 最大回撤, 720d PF, Recovery, Sharpe 等)。任一未过 → 等级 淘汰。
_Avoid_: 评分门槛, 必过项

**策略方向 (Strategy Direction):**
策略的入场信号类型 + 出场逻辑的整体范式。例: OB 入场 + HTF target 出场 vs FVG 入场 + Trailing 出场。改变策略方向 = 换范式, 不是调参。
_Avoid_: 策略参数, 策略风格

**根本性调整 (Fundamental Adjustment):**
需要修改 EA 源码 (非 .set 参数) 才能实现的策略变更。例: 增加新入场类型, 改造出场机制。区别于"参数调整"。
_Avoid_: 代码修改, 重构

**Anchor Strategy (锚策略):**
通过 YAML `&anchor_name` 定义的策略基底, 后续策略通过 `<<: *anchor_name` 继承其全部参数。BTC 现役锚: `v11_btc1_qual232` (WFYS 80.17 基底)。
_Avoid_: 基底, 模板, 基础策略

**Trend Strategy (趋势策略变体):**
基于某锚的浅层参数变体, 命名格式 `v11-btc1-trendNN`。所有 trend 共享同一入场/出场范式, 仅参数不同。区别于"策略方向变体"。
_Avoid_: 趋势变体, 微调

**HTF Target (大周期目标):**
BTC 策略的主出场机制: 取 H4/HTF 的 swing 高/低点作为目标位。trade 在 `htf_min_target_r` (默认 2.2) 和 `htf_measured_move_r` (默认 3.2) 区间内取最远。**与 XAU 的"取 BE + DTP + Trail 渐进步出"截然不同, 是 BTC 的范式特征。**
_Avoid_: 出场目标, 大周期出场

**HTF Skip Flags (大周期跳过标志):**
`htf_skip_dtp: true` + `htf_skip_trail: true` 组合在 BTC profile 中, 表示 HTF target 模式下跳过 DTP 和 Trailing 检查。**这是导致"参数改 DTP/Trail 无效"的根因**。要生效需先 `htf_skip_dtp: false`。
_Avoid_: 跳过 DTP/Trail, 跳过标志

**Bad Bounce (噪声 OB):**
`bounce_ob_pct` (OB 中点位于 OB 区间的 0-1 比例) 落在 `bad_bounce_min_pct` 和 `bad_bounce_max_pct` 之间的 OB, 视为低质量信号。`bad_bounce_mult < 1` 缩仓位, `bad_bounce_mult <= 0` 直接 BLOCK。
_Avoid_: 噪声 OB, 低质量 OB

**Big Win Ratio (大赢单比例):**
`>3R 大赢单 / 总赢单` 的比例, WFYS `趋势利润结构`模块的核心子分。当前 BTC trend111: 23.8% (9/38), 目标 40%+。
_Avoid_: 大赢率, 大胜率

**Trade Count Target (交易数量目标):**
"一周至少 3 单" = 24 个月 ≥ 288 笔。当前 BTC trend111: 117 笔 (1.1/周), 需 2.5x 提升。
_Avoid_: 交易频率, 每周单数

**Structural Limit (结构上限):**
策略在参数 + 单点代码改动下能达到的 WFYS 分数上限。BTC OB 策略的结构上限: ~87 (trends 111/112), 突破需"根本性调整"或"策略方向变体"。
_Avoid_: 参数上限, 优化极限

**Wider Stop Loss (宽止损):**
相对窄 SL (1.0-1.5 ATR) 而言, 2.0+ ATR 的 SL 配置。trend01 验证"宽 SL 单独作用证伪" — 让亏损单变得更大, 盈亏比反而下降。
_Avoid_: 大止损, 宽 SL

**OB Confirmation Quality (OB 入场确认质量):**
OB 触发后的多重确认 (bounce close, entry depth, context, HTF shape 等) 决定入场质量。当前 BTC qual232 链条包含 ~10 层过滤。
_Avoid_: 入场过滤, 信号确认

## Relationships

- 一个 **Strategy Direction** = 一种 **Entry Signal Type** + 一种 **Exit Mechanism** + 一种 **Position Management**
- 当前 BTC 主导 **Strategy Direction** = **OB Entry** + **HTF Target Exit** + **HTF Skip DTP/Trail**
- **HTF Target Exit** 在 BTC 中**屏蔽了** DTP / Trail / NoMFE 等子退出机制
- **Big Win Ratio** 与 **Trade Count** 存在**此消彼长**: 滤掉低质量 entry → trade 变少但每笔质量提升 (大赢单变多)
- **Anchor Strategy** 与 **Trend Strategy** 是**继承关系**: Trend 通过 `<<: *anchor` 继承 Anchor 的全部参数, 仅覆盖差异
- **Wider Stop Loss** 单独作用**证伪** (trend01 验证): 不增加 SL 缓冲, 直接扩大 SL 距离

## Example dialogue

> **User:** "禁用 HTF target, 改用 trailing exit 怎么样?"
> **Dev:** "这是 **Strategy Direction** 变更 — 从 **HTF Target Exit** 切换到 **Trailing Exit**。BTC strategy trend181 验证过, 改用 Trailing 后 big_win 从 23.8% 跌到 0% (因为 Trailing 抓不到 HTF Target 那种快速突破), score 从 87.34 掉到 85.11。所以 Trailing 对当前 OB 范式不是简单替换, 需要重做策略。"

> **User:** "那加大仓位能不能解决 3 单/周?"
> **Dev:** "不能, 仓位 (btc_risk_percent, btc_max_lot_size) 与 trade 数量是**正交的两条轴** — 仓位影响每笔 pnl 幅度, OB 检测频率决定 trade 数量。trend02-09 验证了: 仓位从 0.5x 改到 9.0x, trade 数量都保持在 165-211 之间 (误差范围内)。要 3+/周必须从**入场信号源**入手, 而非仓位。"

## Flagged ambiguities

- "根本性调整" 在本次对话中被精确定义为"需修改 EA 源码, 而非 .set 参数"。之前的尝试 (CheckFastSL, CheckLossCut) 虽被标记为"根本性", 但实际只增加了几十行位置管理代码, 仍是"位置管理层的增量改动", 没有跨过入场信号源的范式门槛。
- "3 单/周" 的目标与"93+ 分"在 BTC OB 范式内**结构性冲突**: 趋势111 (87.34) 和趋势186 (62.78, 5+/周) 表明 trade 数量与 WFYS 分数是反比关系。要同时满足需"根本性"跨过 OB 范式本身。

## Plan reference

完整攻关计划见 `research/notes/2026-07-04_btc_93_3perweek_plan.md`。
实现决策见 `docs/adr/`。
