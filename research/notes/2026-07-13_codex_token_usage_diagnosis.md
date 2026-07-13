# 2026-07-13 Codex 回测改进任务 Token 剧增诊断

## 摘要

今日继续执行的 `bv1` 改进任务并不是一个新任务，而是 2026-07-09 创建的长任务。Codex 权威 usage 记录显示：

- 任务累计：**354,409,198 raw token**。
- 任务累计非缓存等效：**5,195,734 token**。
- 2026-07-13 当日新增：**84,937,362 raw token**。
- 当日新增非缓存等效：**1,719,481 token**。

根因不是 MT5 运行了 29 次回测，也不是少数大日志，而是：

> **50 万级长上下文 × 高频工具调用 × 错误的回测轮询方式 × 三次冷缓存恢复。**

16:14 提交 `3b9a143b` 所称“实际约 46M、只是旧估算误报”不成立。46M 是按结果文件数量乘人工常数得到的回测工作量估计，不是 Codex token。

## 调查范围与安全约束

- 权威任务记录：`C:\Users\Gnef\.codex\state_5.sqlite` 的 `threads.tokens_used`。
- 权威 token 明细：目标 rollout 中的结构化 `event_msg/token_count`。
- 非缓存等效核对：`C:\Users\Gnef\.codex\goals_1.sqlite` 的 `thread_goals.tokens_used`。
- 只抽取 token 数、时间戳、工具名、命令分类和输出字节数。
- **未整份读取或输出原始 Agent 日志，未输出消息正文或工具输出正文。**

目标 rollout：

```text
C:\Users\Gnef\.codex\sessions\2026\07\09\
rollout-2026-07-09T10-35-19-019f44ba-b5ce-7d81-bb09-d80ebbb7e121.jsonl
```

复现命令：

```bash
python scripts/codex_token_audit.py <上述 rollout> --date 2026-07-13 --tz-offset 8
```

## 计量口径

| 口径 | 公式 | 用途 |
|---|---|---|
| Raw | `total_tokens` | Codex 处理的总上下文量，包含缓存输入 |
| 非缓存等效 | `input - cached_input + output` | 与 goal 用量一致，更接近配额/冷缓存影响 |
| 回测工作量 | smoke/90d/720d/WFYS 人工点数 | 仅限制实验规模，**不是 token** |

目标任务末值：

```text
input              354,113,145
cached_input       349,213,464
output                 296,053
raw total          354,409,198
非缓存等效           5,195,734
```

## 当日证据

### 1. 上下文回放是主因

当日 84,937,362 raw token 中：

- input：84,868,456（raw 的 **99.919%**）
- cached input：83,217,881（input 的 **98.06%**）
- output：68,906
- reasoning output：0（usage 记录口径）

单次 API 输入从任务最初的 15,383 增长到今日末尾 581,277，增长 **37.8 倍**。任务模型上下文窗口为 950,000，未发生足以把历史压回小上下文的压缩。

### 2. 今日速率较 7 月 9 日高 57%

| 日期 | 活跃时间 | Raw 增量 | usage 事件 | 工具调用 | Raw/活跃分钟 |
|---|---:|---:|---:|---:|---:|
| 2026-07-09 | 268.9 min | 269.47M | 1,065 | 1,060 | 1.00M/min |
| 2026-07-13 | 54.1 min | 84.94M | 165 | 156 | 1.57M/min |

同样一次工具调用，今日需要携带约 49–58 万输入 token，因此单位时间用量更快。

### 3. 回测轮询是最大可控浪费

今日工具调用：

- 156 次 function call
- 152 次 `exec_command`
- 88 次回测进程/结果轮询
- **0 次 `write_stdin`**

典型错误模式是反复新建：

```powershell
Start-Sleep -Seconds 1500
Get-Process ... terminal64|metatester
Get-ChildItem results/backtest ...
```

同一条 `bv3` 轮询命令重复 10 次，配套状态命令重复 10 次；`bv4` 分别重复 9 次；`loop144` 分别重复 7 次。Agent 没有复用 exec 返回的 session id，而是约每 40 秒创建新轮次。

按 token_count 前置动作归因，94 个轮询相关 usage 事件消耗约 **47.49M raw**，占当日 raw 的 **55.9%**。缓存降低了其非缓存成本，但仍制造了大量上下文处理和 PTY/进程管理噪音。

### 4. 三次冷缓存造成界面阶跃

当日检测到三次单次非缓存输入超过 100K 的事件：

| 时间 | input | cached | 非缓存等效 |
|---|---:|---:|---:|
| 12:45:32 | 492,858 | 227 | 495,828 |
| 15:22:00 | 525,372 | 114 | 525,357 |
| 15:35:46 | 557,336 | 114 | 557,625 |

三次合计 **1,578,810 非缓存等效 token**，占当日 1,719,481 的 **91.8%**。这解释了“用量突然跳”的主观体验：长任务恢复/新 turn 发生缓存未命中时，会一次性重传整段 50 万级上下文。

### 5. 大输出不是主因

- 今日全部工具输出仅 75,796 bytes。
- 整个任务全部工具输出约 740KB。
- 最大单次工具输出约 10KB。

所以不是“某一份巨大回测日志灌入上下文”，而是 1,216 个小工具结果与调用长期累积，随后每轮被再次带入输入。

### 6. 16:19 副本没有重复计费

16:19 前后出现 5 个同标题归档任务，均显示 354,409,198。逐行归一化比较：其中 4 份除新 `session_meta` 外与原 rollout 的 4,278 行完全相同；没有新增 `token_count`。另一份只有 8 个任务恢复元数据事件，也没有新增 usage。

结论：这是任务恢复/归档复制，不能把 354.4M 乘以 5；不是五次重复模型执行。

## 假设判定

| 排名 | 假设 | 判定 | 证据 |
|---:|---|:---:|---|
| 1 | 长上下文回放放大 | ✅ 主因 | 单次 input 15K → 581K；input 占 raw 99.919% |
| 2 | 回测等待高频轮询 | ✅ 主因 | 88 次轮询、0 次 write_stdin；归因 47.49M raw |
| 3 | 大块工具输出 | ❌ 排除 | 今日输出仅 75.8KB，最大约 10KB |
| 4 | xhigh + 无界目标 | ⚠️ 放大器 | “无限时间、不断闭环”扩大轮数；当日 reasoning usage 不是主量 |
| 5 | 任务副本重复消费 | ❌ 排除 | rollout 主体完全相同，无新增 token_count |

## 16:14 修复为何无效

提交 `3b9a143b` 存在四个问题：

1. `measure_actual_tokens()` 没有读取任何 Codex usage，只按回测报告数量乘 5M/1M/0.35M 人工常数。
2. 新增的 `estimate_tokens_v2()` 没接入主流程；主流程仍调用旧 `estimate_tokens()`。
3. `files_count = n_720d + n_90d + n_wfys` 把不同产物当成独立变体，再乘 6.5M，发生语义重复。
4. 回归测试依赖当日未跟踪的 `results/backtest` 文件，并把 40–55M 人工区间断言成“实际 token”。

本次已前向修复，不 revert 他人提交：

- `_loop_batch.py` 改用“回测工作量点数”，CLI 改为 `--workload-budget`。
- 旧 `--token-budget` 只保留隐藏兼容别名，并明确警告不代表 token。
- 新增 `scripts/codex_token_audit.py`，真实读取 `token_count`。
- 测试改用自包含 fixture，不依赖当天回测产物。

## 防复发规则

1. **长回测只启动一个 exec session。** 返回 session id 后只用 `write_stdin`。
2. `write_stdin` 使用 `yield_time_ms=300000`，最多每 5 分钟检查一次。
3. 禁止用新的 `Start-Sleep` 命令轮询同一个回测。
4. 单次 input ≥200K：阶段结束后 handoff 到新任务。
5. 单次 input ≥400K：停止开新实验，只允许提交、反思、handoff。
6. 每个 Loop 的 Reflect/Gate/commit 是默认任务边界，不在同一任务中无限追加 Loop。
7. 真实 token 只认 rollout `token_count`；回测文件只能用于计算工作量。

## 预期收益

- 消除 88 次轮询中的绝大多数轮次，可直接去掉约 47.49M raw 上下文处理。
- 避免在 50 万级任务中三次冷启动，可避免约 1.58M 非缓存等效 token。
- 新任务若把单次输入恢复到 20K–100K，同样工具调用数量的 raw 用量预计下降 80% 以上。
