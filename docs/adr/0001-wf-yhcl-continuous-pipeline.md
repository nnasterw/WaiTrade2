---
status: accepted
---

# wf-yhcl 项目化并采用同会话持续迭代流水线

WaiTrade2 将 `wf-yhcl` 作为项目内版本化技能和唯一完整策略迭代入口，仓库 `scripts/_loop_*` 作为唯一执行内核；所有 Loop 在同一 Codex 会话中连续运行并依赖自动压缩，不使用 token 熔断、节流或跨任务轮换。每个 Loop 受 12 点/30 分钟/3 个单变量假设约束，生成权威 JSON Manifest、人类可读检查点、完整证据清单和真实 Token 用量归因；确认结构上限时必须先进入盈利结构发现，再在下一 Loop 验证一个最高优先级结构。

## 考虑过的方案

- 保留用户目录中的独立技能：拒绝，因为技能、策略代码和测试会漂移。
- 同时保留 `_loop.py`、`_yhcl31.py`、`wfyhcl_phase.py` 三个平级入口：拒绝，因为治理规则可被绕过且已有重复实现。
- 每 Loop 创建新 Codex 任务：拒绝，持续迭代要求保持同一会话并依赖自动压缩。
- Token 超阈值停止或节流：拒绝，Token 只记录和归因，不改变持续迭代行为。

## 后果

- 项目目录 `.agents/skills/wf-yhcl` 是技能权威源码，全局技能路径通过 Windows Junction 指向它。
- `scripts/wfyhcl_governed.py` 是权威状态机；外部技能脚本只做兼容转发。
- 达到 WFYS 93+ 且周均单数不低于 2 后生成毕业候选、提升 baseline 并继续研究，但绝不自动部署 Live。
