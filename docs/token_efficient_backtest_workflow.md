# 低 Token 回测分析工作流

目标: 后续策略迭代只把结构化摘要交给模型，不直接读取原始日志、完整 CSV 或大矩阵。

## 常规回测

后台回测并压缩终端输出:

```bash
python3 scripts/mt5_cli_backtest.py --background --brief --strategy v11b_xau_r31_m1_tp15 --symbol XAUUSDm --from 2025.06.01 --to 2025.07.01 --deposit 200 --timeout 900
```

`--brief` 只输出每个品种一行 `BRIEF ...`，完整报告仍会保存到 `results/backtest/`。

## 报告摘要

只看核心指标:

```bash
python3 scripts/backtest_digest.py --report results/backtest/xxx.txt --brief
```

需要逐单归因时才显式传 `--log` 或 `--export-csv`。`--brief` 默认不会扫描 MT5 Agent 日志目录。

## 结果仓库

将全部 `.txt` 回测报告转成 JSONL:

```bash
python3 scripts/backtest_ledger.py build --reports-dir results/backtest --output results/backtest/backtest_ledger.jsonl
```

用 ledger 查月度缺口:

```bash
python3 scripts/backtest_ledger.py query-monthly \
  --ledger results/backtest/backtest_ledger.jsonl \
  --start 2024.06 --end 2026.05 --available-to 2026.05.26 --target-balance 270 \
  --leg xau_r31:XAUUSDm:v11b_xau_r31_m1_tp15 \
  --leg xau_r27:XAUUSDm:v11b_xau_r27_m1_pf2_hourcut
```

## CSV 归因

不要整份读取 `.trades.csv`。先本地聚合:

```bash
python3 scripts/trade_cluster_summary.py --csv results/backtest/xxx.trades.csv --top 3
```

输出仅包含总 R、正/负贡献小时、退出方式贡献。
