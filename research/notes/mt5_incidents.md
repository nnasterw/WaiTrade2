# MT5 事故与解决方案汇总

## 1. 终端 `rm -rf Tester/` 灾难（2026-06-11）

**事故**：回测脚本中 `sh.rmtree(tdir)` 删除了 `Tester/` 全部内容，包括 `Tester/bases/Exness-MT5Trial5/history/XAUUSDm/*.hcs`（tick 历史缓存）。

**后果**：终端无法执行 Model 4 回测，所有回测失败。

**解决**：
- 从 QS Live 终端复制 `Tester/bases/` 恢复
- 注意：bases 必须在 `Tester/bases/` 子目录下，不是终端根目录
- Exness 会在终端在线时自动重新下载缺失的 tick 数据

**教训**：
- **只删除 `Tester/cache/`，不动 `Tester/bases/`**
- 不做 `rm -rf Tester`——等于删除 MT5 回测引擎核心数据
- 保持一份 `Tester/bases/` 的备份

---

## 2. `/config:` 路径静默截断（2026-06-11）

**事故**：INI 文件放在项目深层目录，路径超过 50 字符。MT5 静默截断路径——日志显示 `launched with D:\Code\codexProject\WaiTrade2`（只到项目名），回测静默失败。

**后果**：5 小时反复尝试回测全部失败，无任何错误提示。

**解决**：INI 放在终端根目录，用短名（如 `bt.ini`），`/config:bt.ini`。

**教训**：
- `/config:` 路径不超过 50 字符
- MT5 **不会报错**，静默失败——日志是唯一线索
- 用 `terminal64.exe /portable /config:bt.ini` 从终端目录启动

---

## 3. Admin 提权改变工作目录（2026-06-11）

**事故**：`Start-Process -Verb RunAs` 提权后 PowerShell 工作目录变为 `C:\Windows\System32`，相对路径 `/config:bt.ini` 解析失败。

**后果**：MT5 日志显示 `cannot load config "D:\Code\codexProject\WaiTrade2\bt.ini"`——路径错误。

**解决**：
- 用 `-WorkingDirectory` 参数指定工作目录
- 或者先 `cd` 到终端目录再启动（非 Admin 模式下有效）
- 最佳实践：Admin 模式下用绝对短路径

---

## 4. 便携终端只允许单实例（2026-06-11）

**事故**：Live 终端运行时，同目录启动第二个 `terminal64.exe /portable` 会静默失败——不报错、不执行回测。

**后果**：多次"NO REPORT"，浪费时间排查。

**解决**：
- 回测前先 `taskkill /F /IM terminal64.exe`
- 注意：Admin 权限运行的终端需要 Admin 权限才能杀
- 提权杀：`Start-Process powershell -Verb RunAs -ArgumentList 'Stop-Process -Force terminal64'`

---

## 5. INI 分号 `;` 被当注释符（2026-06-11）

**事故**：INI 文件中用 `;` 分隔多个参数在一行：
```ini
Expert=WaiTrade3\WaiTrade_OB_SMC; ExpertParameters=v3-mtf.set
```
MT5 将 `;` 后全部视为注释 → `ExpertParameters` 参数丢失 → EA 不回测。

**后果**：多次回测 0 交易，`.set` 文件未被加载。

**解决**：INI 每参数独立一行，不用分号：
```ini
Expert=WaiTrade3\WaiTrade_OB_SMC
ExpertParameters=v3-mtf.set
```

---

## 6. Exness Demo Tick 数据不完整（2026-06-11）

**事故**：Exness demo 账户仅提供 3MB/年的 `.hcs` tick 文件（应有 50-200MB）。Model 4 回测时 MT5 优先用真实 tick，数据稀疏→交易数暴跌 75%。

**后果**：v2 基线从 122 笔降至 41 笔，v3-mtf 从预期 122 笔降至 41 笔。所有回测结果偏低。

**解决**：
- **回测前删除 `.hcs` 文件**：`rm Tester/bases/*/history/XAUUSDm/*.hcs`
- Model 4 退化为生成 tick（从 M1 OHLC 生成），质量接近真实 tick
- 或者 `ProxyEnable=0` 阻止终端连接 Exness 下载不完整数据

**教训**：Exness demo tick 数据不可信。回测标准流程应显式删除 `.hcs` 确保一致的测试环境。

---

## 7. 终端缓存导致重复结果（2026-06-11）

**事故**：同一 `Report=` 名称的回测结果被终端缓存。修改参数后重新跑，报告内容不变。

**后果**：v2 和 v3 测试返回完全相同的 $220.68/122 笔，误判为 v3=v2。

**解决**：每次回测用唯一 `Report=` 名称，并删除 `Tester/cache/`。

---

## 8. v3 参数默认 true 破坏向后兼容（2026-06-11）

**事故**：`ConfigSMC.mqh` 中 4 个 input 默认 `true`：
- `InpEdgeBounceOnly`
- `InpOBFreshnessFilter`
- `InpMTFBlockCounterTrend`
- `InpStructureBlockCounterTrend`

加载 v2 `.set` 时这些参数不在文件中→使用源码默认 true→v3 EA 意外过滤掉大部分交易。

**后果**：BD07/RegimeBoth/PathB 在 v3 EA 上零交易（$0/0笔），误判 v3 不兼容 v2。

**解决**：所有新增 input 默认值改为 `false`/`0`/`0.0`。策略 YAML 中显式设为 `true` 来启用。

**教训**：铁律 #17——v3 所有新参数必须默认禁用。

---

## 9. `CopyRates` 索引反转（2026-06-11）

**事故**：BOS Retest 代码中 `h1_rates[h1_lookback - 1].close` 和 `h1_rates[h1_lookback - 2].close` 读取了最旧的 K 线（索引 N-1/N-2），而非最新 K 线（索引 0/1）。MT5 `CopyRates` 中索引 0 = 最新 bar。

**后果**：BOS Retest 永远检测不到 swing 突破。

**解决**：改为 `h1_rates[0].close`（当前）和 `h1_rates[1].close`（前一根）。

---

## 10. `CopyRates` H1 历史不足（2026-06-11）

**事故**：BOS 检测要求 `h1_lookback >= 30` 根 H1 bar。回测起点（如 5 月 1 日 00:00）只有 1-2 根 H1 bar（当前 + 前一根），函数提前退出。

**后果**：BOS Retest 在回测初期（前 30 小时）完全不工作。

**解决**：阈值从 30 降为 10。同时将 swing 突破检测从收盘价改为高/低点突破（增加灵敏度）。

---

## 11. MT5 Agent 日志跨运行累积（2026-06-11）

**事故**：Agent 日志文件（`Tester/Agent-*/logs/YYYYMMDD.log`）跨多个回测运行持续追加。新旧运行的日志混合，搜索 `[BOS]` 关键词时匹配到旧运行的输出。

**后果**：误判 BOS 诊断在新代码中仍然工作（实际是旧运行的残留日志）。

**解决**：检查日志时间戳（`CS 0 HH:MM:SS`），或在每次回测前清理日志。

---

## 总结

| # | 事故 | 根因 | 影响 |
|:--:|------|------|:--:|
| 1 | 误删 Tester | 脚本写法 | 回测瘫痪 |
| 2 | 路径截断 | MT5 静默 bug | 5h 无效排查 |
| 3 | Admin 换目录 | 提权副作用 | INI 找不到 |
| 4 | 单实例 | 便携模式限制 | 静默失败 |
| 5 | 分号注释 | INI 格式误解 | .set 不加载 |
| 6 | 不完整 tick | Exness demo | 交易数-75% |
| 7 | 结果缓存 | 同名 Report | 结果重复 |
| 8 | 默认 true | v3 向后兼容 | 零交易 |
| 9 | 索引反转 | CopyRates 误解 | BOS 不触发 |
| 10 | H1 不足 | 阈值太保守 | BOS 初期不工作 |
| 11 | 日志累积 | 跨运行追加 | 诊断误判 |
