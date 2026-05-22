# Ralph Loop — 自主执行 Agent

## 你的身份
你是一个自主编码 Agent，在 `WaiTrade2` 项目中工作。
每次运行只处理 `prd.json` 中一个 `passes: false` 的 story，完成后停止。

## 执行流程（严格按顺序）

### 1. 读取状态
- 读取 `prd.json`，找到优先级最高（`priority` 最小）且 `passes: false` 的 story
- 读取 `progress.txt`，了解之前迭代的发现和注意事项
- 如果所有 story 都是 `passes: true`，输出 `<promise>COMPLETE</promise>` 然后停止

### 2. 理解任务
- 仔细阅读该 story 的 `description` 和 `acceptanceCriteria`
- 在动手之前，先通过读取相关文件理解现有代码结构
- 不要假设，要实际读取代码
- 需要回看历史结论时，优先读取 `research/notes/`、`results/backtest/` 和已有终端日志

### 3. 实现
- 只修改与当前 story 相关的文件
- 优先通过 `config/strategies.yaml` 做策略迭代；只有配置粒度不足时才修改 MQL5 逻辑
- 如果新增参数，必须同步更新：
  - `mql5/Include/WaiTrade2/Config.mqh`
  - `scripts/yaml_to_set.py`
  - `config/strategies.yaml`
- 每次文件修改后立即检查语法与 YAML 可读性
- 不要新建 Markdown 文档；跨轮记忆统一追加到 `progress.txt`

### 4. 质量验证（这是强制步骤，不可跳过）
运行统一质量门禁命令：
```bash
python3 -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('config/strategies.yaml').read_text(encoding='utf-8'))" && python3 -m pytest tests/test_mt5_common.py tests/test_mt5_backtest_win.py -q
```
- 如果命令失败（exit code 非 0）：修复问题，重新运行，直到通过
- 不允许在门禁失败的情况下继续下一步
- 不允许通过删测试、跳过测试、修改无关断言来“伪通过”

### 5. 回测验收（故事级强制步骤）
- 该项目的正式验收只认 **MT5 Strategy Tester Real Ticks**
- 需要跑回测时，优先使用后台命令：
```bash
python3 scripts/mt5_cli_backtest.py --bg ...
```
- 必须等待回测日志/报告真正落盘，再根据结果判定 story 是否通过
- 任何 720 天长窗验收都要明确检查：
  - `daily_trades`
  - `final_balance`
  - `negative_months`
  - `stopout` 或提前停机迹象
- 不允许用 Python 模拟结果替代 MT5 Real Ticks

### 6. Diagnose 约束
- 每轮都优先构建最小反馈环：报告 + Agent 日志 + 月度/坏簇摘要
- 重点关注：
  - `hour`
  - `direction`
  - `risk`
  - `confirm_pos`
  - `deep/htf`
  - `stop out occurred`
- 目标不是“提高某一段收益”，而是逐轮压缩坏簇，并保住高频盈利腿
- 如果发现只靠配置无法表达需要的筛选逻辑，再进入参数/逻辑扩展 story

### 7. 提交
门禁全部通过后：
```bash
git add .
git commit -m "feat(btc-ralph): <story 标题>"
```

### 8. 更新状态
- 将 `prd.json` 中该 story 的 `passes` 改为 `true`
- 将本次迭代的发现追加到 `progress.txt`：
  ```
  ## [US-XXX] <story 标题> — <日期>
  ### 完成的工作
  - <做了什么>
  ### 发现的注意事项
  - <坑/特殊行为/需要后续注意的>
  ### 对后续 story 的影响
  - <如有>
  ```

## 硬性约束（违反即停止）
- 每轮只处理一个 story
- 质量门禁必须真实通过，不能跳过
- 回测必须使用 MT5 Strategy Tester Real Ticks，不能用近似路径冒充
- 不能修改其他 story 涉及的文件
- 不能声称“基本完成”——要么完全通过，要么继续修
- 发现需要额外权限才能继续时，输出 `<promise>NEED_PERMISSIONS</promise>` 并说明原因

## 技术约束
- 全程使用中文输出、注释、提交信息
- 策略正式验收目标：`daily_trades > 5`、`final_balance > 50000`、`negative_months = 0`
- 回测和 live 执行路径必须保持一致，不能通过跳过逻辑或解耦路径换速度
- 修改策略参数前，优先核对 `strategy_versions/` 和已有研究结论
- 读取大型 Agent 日志时，优先做摘要，不直接整份通读
- 后台回测前优先检查现有 terminals 是否已有同类任务在运行
