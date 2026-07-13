---
name: wf-yhcl
description: |
  WaiTrade2 的持续受控策略迭代技能。基于订单级趋势结构、订单块质量、持仓路径和出口机理生成可证伪的单变量假设，调用项目 governed runner 执行 30d→90d→最多一个 720d 的 Model 4 晋级验证，并生成证据包、Manifest、Loop 检查点、自动 Gate 和真实 Token 用量归因。用于 BTC/XAU 策略诊断、亏损根因分析、WFYS 改进、盈利结构发现、结构上限后的架构探索，以及用户要求持续、不间断地分析—改进—回测时。
---

# wf-yhcl

只通过项目状态机执行完整迭代：

```powershell
python .agents/skills/wf-yhcl/scripts/wfyhcl_phase.py status
python .agents/skills/wf-yhcl/scripts/wfyhcl_phase.py governed-iterate --plan <plan.json>
```

## 不可违反

1. 保持同一 Codex 会话持续运行；每个 Loop 写检查点，依赖 Codex 自动压缩继续。
2. Token 只记录和归因，不停止、不节流、不换任务。
3. 每 Loop 最多 3 个假设，每个普通变体只改 1 个变量。
4. 执行 30d smoke → 90d → 最多 1 个 720d → WFYS；正式回测只认 Model 4 / Real Ticks。
5. 回测前必须通过策略一致性、Iron Rule strict、Preflight、Period/BarTF 和 `.ex5` 来源检查。
6. 默认初始资金 `$200`；禁止按小时、日期或月份构造后视镜过滤器。
7. 长回测只启动一个 exec session，后续用 `write_stdin` 等待；禁止新建 `Start-Sleep` 轮询。
8. 原始报告、逐笔交易、月度归因和 WFYS 形成证据包；只按证据请求读取必要范围，禁止整份读取 Agent 日志。
9. Gate 必须在结果后自动决定，不得预填“继续深挖”。
10. 确认结构上限时进入盈利结构发现 Loop；下一 Loop 只验证一个最高优先级结构。
11. 每 Loop 形成一个本地提交；关键最佳、架构变化、方向关闭和重大修复才推送。
12. 达到 WFYS 93+、周均不低于 2、零硬失败后生成毕业候选并继续研究；绝不自动部署 Live。

## 标准流程

```text
读取 current_pipeline.json 和最新 Manifest
→ 按需读取证据包
→ L1/L2 Diagnose；red flag 才进入 L3
→ 生成最多 3 个 ranked 单变量假设及预测/证伪条件
→ 写机器可读 plan.json
→ governed-iterate
→ 证据驱动 Gate
→ Manifest + Markdown 检查点 + Token 归因
→ 本地 Loop 提交
→ 同一会话立即进入下一 Loop
```

## Gate

- **继续当前方向**：证据支持同一假设族继续。
- **切换假设**：当前假设证伪，但方向仍有独立根因。
- **重构架构**：结构上限证据成立，先做盈利结构发现，再决定代码改动。
- **方向关闭**：方向已证伪或穷尽；自动重新 Diagnose，不停止流水线。

结构上限可由直接执行路径证明确认；否则需 3 个连续 Loop、最多 9 个有效假设且覆盖至少 3 个独立维度。参数未生效不算结构上限。

## 资源按需加载

- 常规 L1/L2/L3 与字段：读取 `REFERENCE.md`。
- Tick、AI 特征搜索、过滤栈和结构级别：仅在盈利结构发现或明确 red flag 时读取 `ADVANCED.md`。
- 兼容诊断：`scripts/batch_diagnose.py` 默认只读已有 720d 证据，不运行 24 个独立月回测。
