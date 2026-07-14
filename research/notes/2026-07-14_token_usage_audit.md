# 2026-07-14 昨晚 token 剧增排查报告

## 真实数字
- session 文件: 4MB, 2442 行, 480 轮 token_count
- last_token_usage 累加: input 219M, output 383K, cached 214M
- context_window 固定 950K, avg%ctx 从 13T08 9% 增长到 14T03 74%
- 凌晨 3 点 14T03: 35 轮 23.5M input, avg 702K/轮 (74% ctx)
- 13T15: 157 轮 74.4M (avg 497K, 52% ctx)
- 13T16: 135 轮 79.0M (avg 614K, 65% ctx)
- 13T12: 18 条 user 但只有 184 bytes (短确认)

## 根本原因
1. history 没有 compaction
   - 每轮 model 把所有之前 messages 重新打包 input
   - context_window 950K 几乎填满 (从 9% 增长到 74%)
2. user 实际消息极少 (~15K tokens, 44 条 input_text)
3. 真正 input 全部是 cached history 重发
   - cached 214M 占 97.7% (说明 cache 命中但仍然按 full tokens 计费)
4. 13T15/16 段 input avg 497K-614K 是 history 持续累积
5. output/input = 0.17% — 每次调用产出 < 1% 新内容, 其余是重发
6. user 35 条 "codex_internal_context goal" 续接导致 system 每 turn 自动注入完整 objective + budget

## 优化点 (不及预期)
- model: MiniMax-M3 with reasoning_effort=xhigh
  - high reasoning 显著增加 reasoning_tokens
- input 70% from history, 30% from user/dev
- tool_calls 实际 0 (function_calls type 0 hit) — agent 内部回合不调用 tool
- 多次 "继续" 续接 → 同一 session 累积 ~480 轮, history 难以压缩

## 真实使用效率
- total input_text (user+dev): 61,737 bytes ~ 15K tokens
- total output+reasoning (asst): 111,602 bytes ~ 28K tokens
- 但实际 token 消耗 219M input / 383K output → 大部分重复 history

## 优化建议
1. context compaction — 应该每 N 轮自动 summary history
2. 拆分长 session — 每 100-150 轮分一个新 session
3. 用 grep/file 等 selective tool 减少 history 累积
4. system prompt minimization — 削减 CLAUDE.md/AGENTS.md 内容
5. 避免 "继续" 续接 (会自动注入完整 goal context)
6. 控制 reasoning_effort (xhigh 显著增加 tokens)
7. cache 优化: model 不要把全部 history 重新打包

## session statistics
- 480 rounds, 219M input / 383K output
- 凌晨 3 点 14T03 35 轮 23.5M 是异常点 (与 14T03 凌晨我开始排查 token 用量剧增这个任务相关, 当时 user 在用我分析)

## 正确的 shell 用法
- powershell 下用 `$env:VAR` 替代 bash 的 `$VAR`
- powershell 下用 `$env:MT5_HOME='...'` 设置环境变量
- 用 `Get-Process | Where-Object` 替代 `ps`/`tasklist`
- 用 `Test-Path` 替代 `ls -la`
- 用 `Get-ChildItem -File | Where-Object` 替代 `find/grep`
- 用 here-string `@'...'@` 替代嵌 `$`/`"` 字符串的 python -c
- 长 python 用 stdin (echo) 或 here-string, 避免 shell 解析
- 用 `python` heredoc `@'...'@ | python -` 跑长代码