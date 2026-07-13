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

**结构上限证据 (Structural Limit Evidence):**
由执行路径的直接架构证明或跨独立维度的连续经验收敛确认当前策略方向无法靠参数迭代突破的证据。
_Avoid_: 单次失败、参数未生效、相邻值无差异

**Wider Stop Loss (宽止损):**
相对窄 SL (1.0-1.5 ATR) 而言, 2.0+ ATR 的 SL 配置。trend01 验证"宽 SL 单独作用证伪" — 让亏损单变得更大, 盈亏比反而下降。
_Avoid_: 大止损, 宽 SL

**OB Confirmation Quality (OB 入场确认质量):**
OB 触发后的多重确认 (bounce close, entry depth, context, HTF shape 等) 决定入场质量。当前 BTC qual232 链条包含 ~10 层过滤。
_Avoid_: 入场过滤, 信号确认

**持续迭代流水线 (Continuous Iteration Pipeline):**
由连续的 Loop 构成、在同一 Codex 会话内运行且不会因 token 用量终止的策略研究过程。
_Avoid_: 跨任务轮换、token 熔断停止

**证据清单 (Evidence Manifest):**
handoff 中对原始回测证据的可追溯引用集合，供后续分析 AI 按需读取而不嵌入报告正文。
_Avoid_: 报告摘要、完整日志副本、口头路径

**证据包 (Evidence Bundle):**
一个已验证策略变体的原始报告、逐笔交易、月度归因、评分结果和回测来源组成的完整分析证据。
_Avoid_: 单一报告路径、结果摘要、无来源的评分

**证据请求 (Evidence Request):**
分析 AI 为回答一个明确研究问题而对证据包指定范围和用途的按需读取声明。
_Avoid_: 整份日志读取、无目的扫描、重复加载证据

**方向关闭 (Direction Closure):**
确认一个假设族或策略方向已收敛或证伪并返回 Diagnose 的 Gate 决策，不终止持续迭代流水线。
_Avoid_: 停止、结束研究、放弃策略

**流水线暂停 (Pipeline Pause):**
由用户显式触发、停止启动新 Loop 但保留当前研究状态的持续迭代流水线状态。
_Avoid_: 方向关闭、Gate 停止、自动熔断

**修复态 (Repair State):**
安全 Gate 失败后禁止无效回测、修复验证前置条件并在通过后恢复原 Loop 的持续迭代流水线状态。
_Avoid_: 流水线暂停、绕过检查、方向失败

**Loop 工作量预算 (Loop Workload Budget):**
限制单个 Loop 的假设、分级验证和时间投入但不限制持续迭代流水线总 Loop 数的实验预算。
_Avoid_: Token 预算、全局停止额度、无限批次

**晋级验证 (Promotion Verification):**
策略变体按 30d、90d、720d 和 WFYS 逐级筛选且每个 Loop 最多一个变体完成最终验证的实验路径。
_Avoid_: 所有变体直接 720d、并发多变量验证、一次性全量回测

**Loop 检查点 (Loop Checkpoint):**
每个 Loop 完成后保存权威研究状态和证据引用、供同一 Codex 会话自动压缩后继续迭代的恢复边界。
_Avoid_: 跨任务 handoff、上下文轮换、完整对话副本

**Loop 提交 (Loop Commit):**
只包含一个 Loop 所拥有改动和检查点、使该 Loop 可独立追溯与复现的本地 Git 提交。
_Avoid_: 多 Loop 混合提交、git add -A、每 Loop 推送

**流水线清单 (Pipeline Manifest):**
记录一个已完成 Loop 的权威研究状态、证据清单、Gate 结论和下一行动的机器可读交接物。
_Avoid_: Markdown 摘要、最新文件猜测、对话历史

**流水线指针 (Pipeline Pointer):**
指向持续迭代流水线最新有效清单和下一个 Loop 的唯一当前状态引用。
_Avoid_: 目录修改时间、最近文件名、手工记忆

**Token 用量归因 (Token Usage Attribution):**
按 Loop 记录真实 token 增量及其来源但不改变持续迭代流水线执行的研究成本证据。
_Avoid_: Token 预算、Token 节流、Token 熔断

**受控迭代 (Governed Iteration):**
由 wf-yhcl 统一诊断、约束假设并委托 Loop 执行内核完成验证和检查点的规范策略迭代。
_Avoid_: 手工批跑、yhcl31 Phase、绕过 Gate 的回测

**项目技能 (Project Skill):**
与 WaiTrade2 策略代码共同版本化、测试和发布的 wf-yhcl 技能权威源码。
_Avoid_: 用户目录唯一副本、未版本化技能、项目外状态机

**毕业候选 (Graduated Candidate):**
通过全部硬门槛并达到流水线目标、被固化和推送但未经用户授权不得部署 Live 的策略候选。
_Avoid_: Live 策略、自动部署、研究终点

**盈利结构探索 (Profit Structure Exploration):**
确认结构上限后深入趋势细节并寻找更有潜力的入场、出场或持仓管理结构的策略方向探索。
_Avoid_: 方向关闭、参数微调、接受结构上限

**证据驱动 Gate (Evidence-Driven Gate):**
wf-yhcl 在验证结果生成后依据假设、基线和证据包自动选择下一研究行动的 Loop 决策。
_Avoid_: 回测前预填 Gate、默认继续深挖、逐 Loop 等待确认

**盈利结构发现 Loop (Profit Structure Discovery Loop):**
不运行新变体、专门从证据包中发现和预筛更有潜力盈利结构的 Loop。
_Avoid_: 边分析边改代码、参数微调、同 Loop 回测验证

**结构验证 Loop (Structure Verification Loop):**
实现一个最高优先级盈利结构候选并通过晋级验证检验其真实效果的 Loop。
_Avoid_: 同时实现多个结构、Python 回测、跳过 baseline

## Relationships

- 一个 **Strategy Direction** = 一种 **Entry Signal Type** + 一种 **Exit Mechanism** + 一种 **Position Management**
- 当前 BTC 主导 **Strategy Direction** = **OB Entry** + **HTF Target Exit** + **HTF Skip DTP/Trail**
- **HTF Target Exit** 在 BTC 中**屏蔽了** DTP / Trail / NoMFE 等子退出机制
- **Big Win Ratio** 与 **Trade Count** 存在**此消彼长**: 滤掉低质量 entry → trade 变少但每笔质量提升 (大赢单变多)
- **Anchor Strategy** 与 **Trend Strategy** 是**继承关系**: Trend 通过 `<<: *anchor` 继承 Anchor 的全部参数, 仅覆盖差异
- **Wider Stop Loss** 单独作用**证伪** (trend01 验证): 不增加 SL 缓冲, 直接扩大 SL 距离

- 一个 **持续迭代流水线** 由同一 Codex 会话内连续运行的 Loop 构成
- 每个 Loop 的 handoff 携带一个 **证据清单**，后续分析 AI 只在需要时读取被引用的原始证据
- 一个 **证据清单** 引用一个或多个 **证据包**，但不复制其正文
- 一个 **证据包** 对应一个策略变体的一次可追溯验证
- 分析 AI 通过 **证据请求** 自主读取 **证据包** 的必要范围，原始日志和 Tick 数据只能定向提取
- **方向关闭** 结束当前方向并触发新的 Diagnose，但不结束 **持续迭代流水线**
- 只有用户显式触发 **流水线暂停** 才停止启动新 Loop
- 安全 Gate 失败使 **持续迭代流水线** 进入 **修复态**，通过后恢复同一个 Loop
- **修复态** 阻止无效回测但不等同于 **流水线暂停**
- 每个 Loop 受一个 **Loop 工作量预算** 约束，预算耗尽触发收尾而不停止 **持续迭代流水线**
- **晋级验证** 从多个单变量假设中最多产生一个完成最终验证的策略变体
- 每个 Loop 完成一个 **Loop 检查点**，同一 Codex 会话在自动压缩后从该检查点继续
- 每个 **Loop 检查点** 对应一个 **Loop 提交**，关键进展才从本地提交推送到远端
- 每个已完成 Loop 产生一个 **流水线清单**，Markdown handoff 是该清单的人类可读摘要
- 一条 **持续迭代流水线** 只有一个 **流水线指针**，它引用最新有效的 **流水线清单**
- 每个 **Loop 检查点** 包含一次 **Token 用量归因**，归因结果不停止、不降级也不轮换流水线
- **持续迭代流水线** 的每个 Loop 都是一次 **受控迭代**，wf-yhcl 是唯一完整入口
- wf-yhcl 是 WaiTrade2 的 **项目技能**，与受控迭代状态机共同演进
- 达成目标的策略成为 **毕业候选** 并可提升为新 baseline，但不自动部署 Live，也不停止 **持续迭代流水线**
- **Structural Limit** 触发 **盈利结构探索** 而不是 **方向关闭**
- **证据驱动 Gate** 在结果产生后选择继续当前方向、切换假设、重构架构或方向关闭
- **Structural Limit** 使 **证据驱动 Gate** 选择重构架构，并在代码改动前启动 **盈利结构探索**
- **Structural Limit** 必须由 **结构上限证据** 确认，参数未生效和单次失败不构成该证据
- **盈利结构探索** 先产生一个 **盈利结构发现 Loop**，其最高优先级候选由下一次 **结构验证 Loop** 实现和验证

## Example dialogue

> **User:** "禁用 HTF target, 改用 trailing exit 怎么样?"
> **Dev:** "这是 **Strategy Direction** 变更 — 从 **HTF Target Exit** 切换到 **Trailing Exit**。BTC strategy trend181 验证过, 改用 Trailing 后 big_win 从 23.8% 跌到 0% (因为 Trailing 抓不到 HTF Target 那种快速突破), score 从 87.34 掉到 85.11。所以 Trailing 对当前 OB 范式不是简单替换, 需要重做策略。"

> **User:** "那加大仓位能不能解决 3 单/周?"
> **Dev:** "不能, 仓位 (btc_risk_percent, btc_max_lot_size) 与 trade 数量是**正交的两条轴** — 仓位影响每笔 pnl 幅度, OB 检测频率决定 trade 数量。trend02-09 验证了: 仓位从 0.5x 改到 9.0x, trade 数量都保持在 165-211 之间 (误差范围内)。要 3+/周必须从**入场信号源**入手, 而非仓位。"

> **研究者：** “Codex 自动压缩后如何继续当前策略迭代？”
> **开发者：** “同一会话从最新 **Loop 检查点** 和 **证据清单** 恢复状态，并立即进入下一 Loop。”

## Flagged ambiguities

- “确认结构上限”曾被列为方向关闭条件 — 已解决：结构上限必须进入 **盈利结构探索**，不能直接关闭方向

- Token 异常曾被提议触发节流或熔断 — 已解决：只生成 **Token 用量归因**，不改变持续迭代行为

- “handoff”曾表示跨 Codex 任务转交 — 已解决：持续迭代保持同一会话，兼容文件 `handoff.md` 的领域含义统一为 **Loop 检查点**

- “停止”曾同时表示关闭当前方向和结束整体研究 — 已解决：前者统一称为 **方向关闭**，后者统一称为 **流水线暂停**

- "根本性调整" 在本次对话中被精确定义为"需修改 EA 源码, 而非 .set 参数"。之前的尝试 (CheckFastSL, CheckLossCut) 虽被标记为"根本性", 但实际只增加了几十行位置管理代码, 仍是"位置管理层的增量改动", 没有跨过入场信号源的范式门槛。
- "3 单/周" 的目标与"93+ 分"在 BTC OB 范式内**结构性冲突**: 趋势111 (87.34) 和趋势186 (62.78, 5+/周) 表明 trade 数量与 WFYS 分数是反比关系。要同时满足需"根本性"跨过 OB 范式本身。

## Plan reference

完整攻关计划见 `research/notes/2026-07-04_btc_93_3perweek_plan.md`。
实现决策见 `docs/adr/`。
