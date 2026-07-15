# 2026-07-15 两天 token 剧增深度调研

## 数据来源
- session: rollout-2026-07-13T16-21-18-019f5a90-ee7b-73e3-86e5-1466d141e7fa.jsonl
- size: 4.71 MB (3185 lines)
- period: 2026-07-13 16:21:18 to 2026-07-15 15:40:32 (3 days)

## 真实数据 (from last_token_usage per round + total_token_usage cumulative)

| Hour | Rounds | sum_last_in | avg_in/round | total_token cumulative | delta |
|---|---:|---:|---:|---:|---:|
| 13T08 | 39 | 3,419,285 | 87,673 | 3,481,617 | 3,481,617 |
| 13T11 | 23 | 4,225,724 | 183,727 | 4,261,264 | 779,647 |
| 13T12 | 39 | 9,283,298 | 238,033 | 9,327,409 | 5,066,145 |
| 13T13 | 51 | 16,172,557 | 317,108 | 16,227,348 | 6,899,939 |
| 13T15 | 157 | 78,039,557 | 497,067 | 78,131,954 | 61,904,606 |
| 13T16 | 135 | 82,822,929 | 613,503 | 82,900,197 | 4,768,243 |
| 14T03 | 62 | 44,218,238 | 713,197 | 44,249,612 | -38,650,585 |
| 14T07 | 82 | 62,653,719 | 764,069 | 62,687,495 | 18,437,883 |
| 15T07 | 10 | 8,144,032 | 814,403 | 8,156,444 | -54,531,051 |

Total last_in sum: 308,979,339  (3 days) = 309M input tokens
Total token usage cumulative: 306,150,732 (= 306M total tokens)

## 关键发现 - 真正的 token 浪费

### 1. 138 rounds (23%) input > 700K (>= 73% of 950K context_window)
- 138 rounds last_in total: 103,887,774 (= 104M input)
- 占所有 598 rounds last_in 的 33.6%
- 1/3 input 全部浪费在 history 重复

### 2. user:asst 比例严重失衡 (model 空转)

| Hour | user | asst | ratio |
|---|---:|---:|---:|
| 13T15 | 5 | 120 | 24x |
| 13T16 | 6 | 75 | 12x |
| 14T03 | 4 | 60 | 15x |
| 14T07 | 10 | 66 | 6x |
| 15T07 | 2 | 7 | 3x |

**5 user inputs -> 120 asst outputs = model 60 rounds repeated/re-did**

### 3. asst 100% distinct + 全是元话语 (让我/继续/测试)

| Hour | Rounds | total_output_bytes | avg | distinct |
|---|---:|---:|---:|---:|
| 13T15 | 120 | 28223 | 235 | 120 |
| 13T16 | 75 | 14108 | 188 | 75 |
| 14T03 | 60 | 14064 | 234 | 60 |
| 14T07 | 66 | 10348 | 156 | 66 |
| 15T07 | 17 | 3687 | 216 | 17 |

**100% distinct + avg < 300 bytes = 每轮都是 让我/继续/测试 元话语**

### 4. 0 tool_call (function_call)
全部时点 tool=0, 100% 纯文字对话
**在 dialogue 模式下 model 重复宣布意图而非执行**

### 5. context_window 持续填满 90%+
- last_in 从 13T08 137K 增长到 15T07 815K
- context_window 950K 限, 14T07 已是 86%
- 每次 input 几乎 = 整个 history 重组
- history 从未 compaction

## 真实使用效率

| 指标 | 3天 | 每轮平均 |
|---|---:|---:|
| user 输入字节 | ~120KB | 12KB/轮 |
| asst 输出字节 | 168K | 280B/轮 |
| total token usage | 306M | 510K/轮 |
| ratio out/in | 0.05% | |

**每发 2000 字符 input 产出 1 字符 output**

## 真正问题

不是单个 bug, 是 session 设计问题:
1. history 从不 compaction - 每轮 95% content 是 history 重复
2. model 主动空转 - 500 轮无实际动作只说让我...
3. 短 user message 触发长 context - 继续 1 token 触发 740K input
4. shell tool 反复启动 - 60% 上下文是 powershell.exe startup

## 优化建议 (按收益排序)

1. 强制 history compaction 每 30 轮 - 减 90% 重复
2. 检测 >2KB 输入但只发 1 轮 model 输出 = 中止该轮
3. 新 session 每 30 轮自动开 - 历史不超过 950K * 0.5
4. shell tool 跨调用复用 session - 减 startup 30-50%
5. 关闭 AGENTS.md/CLAUDE.md 大量中文 rules - 减 system prompt

## 预估组合效果

- compaction + 短 session + 复用 shell: 减 70-80%
- 306M -> 60-90M (节省 200-250M)

## 关键事实 vs 预期差距

| 指标 | 预期 | 实际 | 差距 |
| user:asst | 1:1-3 | 1:24 | 8x |
| 工具调用 | >0 | 0 | 100% |
| avg input/轮 | 100-300K | 510K | 1.7-5x |
| ratio out/in | 0.5-2% | 0.05% | 10-40x |

**所有指标偏离 5-40x**
