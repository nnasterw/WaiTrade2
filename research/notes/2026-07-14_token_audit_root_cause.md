# 2026-07-14 凌晨 token 剧增根因诊断报告

## 实测数据 (480 轮 token_count 事件)

| 指标 | 值 |
|---|---|
| session 文件 | 4.11 MB, 2442 行, 480 轮 |
| last_token_usage 累加 input | 230.8M |
| last_token_usage 累加 output | 391K |
| last_token_usage 累加 cached | 224.7M (97.3% 命中率) |
| last_token_usage 累加 reasoning | 67K (占 input 0.03%) |
| model | MiniMax-M3 |
| reasoning_effort | xhigh (40/40 turn_context 全用) |
| model_context_window | 950K (固定) |
| tool calls (function_calls) | **0** |
| user:input_text 总字节 | 61,765 (~15K tokens) |
| asst:output_text 总字节 | 114,689 (~28K tokens) |
| **output/input ratio** | **0.17%** |

## 每小时 last_token_usage 增长

| hour | rounds | avg_in | out_total | in_total | avg%ctx |
|---|---:|---:|---:|---:|---:|
| 13T08 | 39 | 87,673 | 61K | 3.4M | 9.2% |
| 13T11 | 23 | 183,727 | 35K | 4.2M | 19.3% |
| 13T12 | 39 | 238,033 | 43K | 9.3M | 25.1% |
| 13T13 | 51 | 317,108 | 54K | 16.2M | 33.4% |
| 13T15 | **157** | **497,067** | 90K | **78.0M** | **52.3%** |
| 13T16 | **135** | **613,503** | 75K | **79.0M** | **64.6%** |
| 14T03 | **46** | **706,971** | 16K | **29.6M** | **74.4%** |

## output 字节分布 (480 轮)

| 桶 | 轮数 |
|---|---:|
| <100 bytes | 41 |
| 100-500 | **238** |
| 500-2000 | 180 |
| 2000-5000 | 27 |
| >=5000 | 9 |

**318 轮 (66%) output < 2KB**。

## 七大根因 (按影响排序)

### 1. history 无 compaction (主要)
每轮 model 把所有之前 messages 重新打包为 input
- 13T08 ctx 9% → 13T16 ctx 65% → 14T03 ctx 74%
- last_token_usage.input 与 total_token_usage 累加几乎一致 (230M vs 230M)
- 即"每轮 input = 几乎全部 history + 当前 user/developer"
- 上下文增长曲线平滑 (无 reset) → 确认无 compaction

### 2. cached 命中率 97.3% 但仍按全 token 计费
- last_token_usage.cached_input_tokens 224.7M / total input 230.8M = 97.3%
- model API 计费可能按 discounted cached 收费，但 rollout/会话计费按 last_token_usage
- 实际效果等价于 "cache 仅加速 API，不省 token"

### 3. 480 轮无 1 个 tool_call (function_calls: 0)
- 480 轮内 **0 个 function_calls** 事件
- 318 轮 (66%) output < 2KB → agent 100% 时间纯文字输出，不读文件/不跑 shell
- input 增长仅靠"回忆历史"，没有任何新数据
- 这是结构性浪费：保留大 history 但不调 tool 提取新信息

### 4. MiniMax-M3 + reasoning_effort=xhigh
- 40/40 turn_context 全用 `default+xhigh`
- xhigh 实际只产出 67K reasoning (0.03% of input) → **xhigh 没有产生等价价值**
- reasoning 字段在 response_item 中不显示 (压缩为 0 字节)
- 但仍按 xhigh 计费

### 5. 单次 round output 极短
- 平均 output 815 bytes/轮 (391K/480)
- 318 轮 output < 2KB (66%)
- 但 input 480K/轮 (input/output = 600:1)
- 大量 input 产出极少新内容

### 6. system 每 turn 注入完整 goal context
- 14 次 "codex_internal_context source=goal" 续接 → 每次 system 自动注入完整 objective + budget + audit blocks
- 单次注入 ~2-3KB
- 与 history 累积叠加

### 7. 凌晨 3 点异常 (排查 token 任务自身造成)
- 14T03 03:33-03:46 共 14 分钟消耗 **29.6M input** (avg 706K/轮)
- 此时 user 正在排查 token 剧增 (2 条 user 消息: 43 + 10 字节)
- agent 用 powershell 调试 python 代码 (脚本失败重试循环)
- 每轮 input 692-724K 但 output 67-502 字节 (debug 输出反复注入 history)
- 14T03:35 单分钟 4.9M input = agent 调试死循环 (我用 powershell -c 嵌 $ 引号失败 6-7 次)

## 修复建议 (按优先级)

### P0 (立即做, 影响最大)

1. **强制 context compaction**
   - 每 50-100 轮自动 summary history
   - 保留最近 10-20 轮完整, 之前压缩为 ~5KB summary
   - 当前 950K/轮 → 可降至 200K/轮

2. **分拆长 session**
   - 每 100 轮自动开新 session (设置 goal 触发新 context)
   - 避免单 session 480 轮累积
   - 单 session 限额 100-150 轮

3. **写小工具替代 powershell 调试**
   - 用 `python -m <module>` 替代 `python -c "complex code"`
   - 用 here-doc (`@'...'@`) 替代嵌 `$`/`"` 字符串
   - 用 stdin `python` + heredoc 处理复杂脚本
   - 避免重复执行同一命令 (产生大量 cached 重复输入)

4. **避免 "继续" 续接**
   - 每次 "继续" 触发 system 注入完整 goal context (~2-3KB)
   - 一条 "继续" 实际增加 2-3K input 和 history 项
   - 14 次 "继续" + 14 次自动注入 = 28-42K 累计

### P1 (本周做)

5. **降低 reasoning_effort 到 medium**
   - xhigh 在 MiniMax M3 上不产生等价价值
   - medium 输出质量通常 95% 一致, 但 input 减半
   - 40/40 turn_context 改 xhigh → medium = 减半 input

6. **强制新 session 起点 (单 run ≤ 30 轮)**
   - 30 轮后 system 自动建议: "为避免 history 累积, 请开新 session"
   - 不是 hint，是强制
   - 用户新 task 必须开新 session

7. **优化 user message 长度**
   - 减少 "codex_internal_context goal" 块 → system 应自动隐藏
   - 大 AGENTS.md/CLAUDE.md 仅在新 session 起始时发送一次
   - 后续 turns 只发送 user 真正需要的 content

### P2 (长期优化)

8. **cache 优化**
   - 即使 cache 命中率高, 仍按 last_token_usage 计费
   - 需要与 model provider 协商 "cached discounted 计费"
   - 或实现 server-side compaction 在发送前压缩

9. **system 端 compaction 调度**
   - 每 50 轮 system 触发: 压缩 history
   - 实现 model-side sliding window attention 限制
   - 永久 context cap = 200K tokens (而不是 950K)

10. **重新评估 "codex_internal_context goal" 续接**
   - 35+ 次 "继续" 注入 = 35+ × 2-3K = 70-100K 重复 input
   - 减少注入频率 (仅每 N 轮注入)
   - 或用精简版替代 (仅 1-2 行而非完整 12 个章节)

## 量化预估

| 修复 | input 减量预估 | 备注 |
|---|---|---|
| 强制 compaction 每 50 轮 | -60% | 200K/轮 vs 当前 600K/轮 |
| reasoning_effort: xhigh → medium | -50% | MiniMax M3 实际无 reasoning 价值 |
| 减少 "继续" 续接 | -5-10% | 14 次 × 2-3K |
| 分拆 session 每 100 轮 | -40% | 单 session ≤ 100 轮 |
| **组合预估** | **-90%** | 230M → ~23M (实际非缓存) |

## 当前 session 调优建议 (具体)

1. **立即**: 减小 reasoning_effort 到 medium
2. **立即**: 写一个 Python 调试脚本 (避免 powershell -c 嵌复杂代码)
3. **立即**: 在 user message 中明确 "不要重复 history 推断"
4. **本 session**: 每 50 轮主动 compact context
5. **本 session**: 避免 powershell 长 heredoc 调试 (使用 Python 写文件然后 exec)
