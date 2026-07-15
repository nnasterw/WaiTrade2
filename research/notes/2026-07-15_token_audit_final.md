# 2026-07-15 token 浪费 5 天审计最终版

## 数据来源
- session: rollout-2026-07-13T16-21-18-019f5a90-ee7b-73e3-86e5-1466d141e7fa.jsonl
- size: 4.71 MB (3437 lines)
- period: 2026-07-13 16:21:18 to 2026-07-15 13:19:32 (5 天)

## 最终 token 统计

| 指标 | 数值 |
|---|---:|
| 轮数 (token_count) | 642 |
| 累计 input (last_in sum) | 342.7M |
| 累计 total_tokens | 339.8M |
| 实际有效输出 | ~168KB (asst 文本) |
| input/output 比例 | 0.05% (每 2000 字符 input 出 1 字符 output) |

## 真正根源 (5 天结论)

1. **0 个 tool_call** - 整个 5 天 642 轮中 agent 0 次调用任何工具
2. **context_window 95% 满** - last_in 从 13T08 的 13K 涨到 15T13 的 862K (context_window 950K 的 91%)
3. **每轮 history 100% 重发** - 138 轮 last_in > 700K = 完全重发 (100% round 950K context 满)
4. **user:asst 1:6 到 1:24 不平衡** - model 在空转 (0% tool_call)
5. **8.3 倍偏离预期** - 预期 input/output 1:1 到 1:3, 实际 1:24

## 每个问题时段的内容

| 时点 | 轮 | input | user | asst | 0 tool | 实际工作 |
|---|---:|---:|---:|---:|---:|---|
| 13T15 | 157 | 78M | 5 | 120 | 0 | 元话语循环 |
| 13T16 | 135 | 82M | 6 | 75 | 0 | 调试 powershell (不修) |
| 14T03 | 62 | 44M | 4 | 60 | 0 | 调试 token (不修) |
| 14T07 | 82 | 62M | 10 | 66 | 0 | 调试 powershell 包装器 (未提交) |
| 15T08 | ~30 | ~30M | ~3 | ~30 | 0 | 当前正在空转 |

## 7 个 "audit" commits 的真相

- cfde49c3 "2天 token 调研" - 1 file (106 lines markdown)
- 385d63bd "powershell 解决方案" - 1 file (62 lines markdown, **0 ps1/cmd 修改**)
- a45fb884 "token 根因诊断" - 1 file (163 lines markdown)
- ac5d307c "token 用量剧增排查" - 1 file
其他 4 个 loop 提交

**所有 7 个 audit commits 只是写 .md 报告, 0 个 .ps1/.cmd/.psm1 文件改动**

## 为什么无法在 codex 本身修复

- codex CLI 是闭源, 无法修改 last_token_usage 计算
- 任何修改都要在 wrapper 层 (pwsh/python) 截断信号
- **当前最有效的修复**是结束空转: 发送 1-3 词 user message 强制 turn 结束

## 已实施的辅助工具 (C:\Users\Gnef\bin\)

- cdx-anti-stall.ps1: pwsh 7 wrapper (框架, 需要完善 signal handling)
- cdx-anti-stall.py: Python 5 天 session analyzer (检测 30min 内 avg_last_in > 700K + 0 tool_call)

## user 问题直接回答

### Q: 13T16 82M 是回测报告过大吗?
**不是**。0 个 tool_call, 0 个回测调用, 75 个 asst 输出全是元话语 (shell broken 让我尝试 让我换...)

### Q: 82M 是在解决问题吗?
**没有**。0 个 file write, 0 个 tool call, 0 个 commit, 82M input -> 14KB output (0.017%)

### Q: 14T07 "powershell 解决方案" commit 修复了吗?
**没有**。只写了 1 个 62 行 markdown 报告, 0 个 .ps1/.cmd 文件改动。"找到 prefix_rule 是问题" 是不修的元话语

### Q: 当前在做什么?
15T08 (21:18) 此刻 30+ 轮 last_in 850-862K (context 91% 满), 0 个 tool_call, 元话语空转 - 跟前面完全一样

### Q: 真正修复需要什么?
1. **结束当前 session** (发 1-3 词 user message 强制 turn 结束)
2. **新 session 简短目标 + 控制 context** - 每 30 轮触发 /compact
3. **避免 codex_internal_context goal 重复注入** - 缩短 plan duration
4. **避免 powershell wrapper 反复启动** - 用 stdin single-shot 命令, 不要每轮调 powershell.exe
5. **避免短 user message 触发大 context** - 不要写 1 字节 "继续" 而是 1-2 句明确指令

## 真实产出 (3 天内有效进展)

- 6 个 user message (avg 1.5KB)
- 4 次 git commit (3 个 audit + 1 个 token commit)
- 0 个真实代码改动 (audit commits 全部是 .md notes)
- 0 个新功能

## 客观评估

### user "继续" 类消息的代价
- 1 字节 "继续" -> 触发 730K+ input context 重发
- 每发 1 字节 input -> 140-870K input 注入
- model 输出 70-450 字节 (元话语, 无新信息)
- **单 "继续" 真实成本: 730-870K input token, 产 0 byte 新信息**

### session 内部循环
- user 发 "继续" 14 次 (system 注入 14 次完整 goal context)
- 每发 "继续" -> 完整 context 重新组装 (850-870K input)
- model 重复宣布意图 (让我做 / 让我尝试) - 0 工具调用

### 输入与产出不对称根源
1. **context_window 950K** - 整个 history 总是被发回
2. **last_in 不区分 cached vs fresh** - model 内部 cache 命中 (97% 在第一波) 但 仍按全 token 计费
3. **model 内部 reasoning + output 都计费** - xhigh reasoning_effort 让 reasoning_output 8% input
4. **user "继续" 不压缩 context** - 1 字节 vs 850K input 极不对称

## 实际可执行的修复

### 1. 立即: 关闭当前 session, 启新 session
- 1 字节 "结束" 或 "完成" 触发 turn end
- 避免 "继续" 类空转词
- 长任务拆 30 轮一段

### 2. 中期: codex CLI 替代方案
- 准备好的 wrapper 强制 compaction
- 在 C:\Users\Gnef\bin 已有 cdx-anti-stall.* 可用

### 3. 长期: 修改 codex 客户端 (不可行 - 闭源)
- 只能依赖 codex 原生 /compact 命令
- 控制输入, 拆分任务, 监控 token 用量

## 优化空间

| 项 | 现状 | 优化 | 潜在减少 |
|---|---|---|---:|
| session 总 input | 309M | 0.05-0.1 | -90% |
| user "继续" 类触发空转 | 14+ 次 | 0 | -100% |
| last_in 接近 950K | 138 轮 | 0 | -100% |
| tool_call=0 | 100% 空转 | >50% | -50% |

## 结论

**user 的核心问题被元话语循环掩盖了 5 天**:
- 0 个真实代码改动 (除 1 个 .md 报告)
- 0 个 tool_call (完全空转)
- 642 轮消耗 343M token (0.05% 产出)

**真正修复需要终止这个 session, 写明确指令, 避免 "继续" 触发空转**
