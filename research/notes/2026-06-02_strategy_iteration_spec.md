# 策略迭代规范 v1.0

> 2026-06-02 基于本轮 Live 审计发现的 10 个问题制定。所有策略相关工作必须遵守。

---

## 一、本轮发现的问题清单（记录以避坑）

### 🔴 致命级

| # | 问题 | 根因 | 教训 |
|---|------|------|------|
| 1 | **回测 TF ≠ Live TF** | `mt5_cli_backtest.py` 只用 `period` 覆盖了 EA 的 `InpBarTF`；策略用 M1 但回测跑 M5，5 倍信号偏差 | 回测 `Period=` 必须从策略 `bar_period_min`/`bar_tf` 读取，不能写死 |
| 2 | **.set 加载失败 → EA 以默认参数裸奔** | `.set` 文件不在 MT5 搜索路径，加载失败后 EA 回退 MQL5 默认参数（无防守、无风控） | 部署后必须验证 EA 日志中的 `InpVersion` 是否匹配预期 |
| 3 | **加载了错误版本的 .set（极端风控版）** | ZD 加载 `zd2.set`（0.1x 仓位 + 1% 暖机 → 死循环永不开仓） | 部署前必须人工确认 `.set` 文件名与策略版本映射 |

### 🟠 严重级

| # | 问题 | 根因 | 教训 |
|---|------|------|------|
| 4 | **QS 基础版 28 分钟连开 9 单** | `max_entries_per_ob=20` + `cooldown=0` + `ob_reentry_cooldown=0` = 无限制重入 | 任何 Live 策略必须有重入上限和冷却时间 |
| 5 | **同一图表先后跑两个版本（QS2→QS），方向相反** | 手动热替换 .set，两个 Magic 号不同但共享 OB 缓存 | 禁止 Live 热替换策略版本；必须重启 EA |
| 6 | **x2.6 仓位在 $200 账户上** | `max_pos_mult=200` + 深度入场 boost → 仓位瞬间放大 | Live 小资金必须严格限制 `max_pos_mult` 和 `max_lot_size` |

### 🟡 中等级

| # | 问题 | 根因 | 教训 |
|---|------|------|------|
| 7 | **ZD 振荡腿全天 ob=0，双腿设计名存实亡** | ZD M3 周期 OB 生成条件严格 + 当日行情偏单边 | 双腿策略应监控各腿活跃度，一腿长期停摆应告警 |
| 8 | **入场诊断日志关闭，无法归因信号跳过** | `InpEnableEntryDebug=false` | Live 必须开启轻量诊断日志 |
| 9 | **2026 年 QS 基础版严重退化：从 $85K/月 → $1.94/月** | 2025 年参数针对超级单边优化，2026 年行情剧变 | 每季度至少重跑一轮 720 天回测验证当前参数 |
| 10 | **无法同时启动两个 portable 终端** | 同一 `terminal64.exe` 只允许一个 `/portable` 实例 | 多实例部署需各自独立复制 `terminal64.exe` |

---

## 二、策略迭代工作流

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1.修改   │ →  │ 2.编译   │ →  │ 3.回测   │ →  │ 4.对比   │ →  │ 5.部署   │
│ 参数     │    │ 验证     │    │ 验证     │    │ 审计     │    │ 上线     │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ▼
                                               ┌──────────┐
                                               │ 6.复盘   │
                                               │ 记录     │
                                               └──────────┘
```

### 步骤详解

#### 1. 修改参数

**必须同步的文件（4 个）：**

| 序号 | 文件 | 说明 |
|------|------|------|
| 1 | `config/strategies.yaml` | 策略定义，YAML 锚点继承 |
| 2 | `scripts/yaml_to_set.py` 的 `FLAT_MAP` | 新增 YAML key 必须在此注册映射 |
| 3 | `mql5/Include/WaiTrade2/Config.mqh` | EA 端 input 变量声明 |
| 4 | `tests/test_mt5_common.py` | 新增参数的测试用例 |

**修改检查清单：**
- [ ] 新参数有明确的 YAML key → InpXxx 映射
- [ ] 策略版本号 `version` 已更新（格式：`V<主版本>-<策略>-<变体>`）
- [ ] Magic Number 唯一，不与任何其他 Live 策略冲突
- [ ] 继承链未被意外覆盖（YAML merge key `<<:` 只覆盖显式字段）
- [ ] `description` 中记录了本次修改的原因

#### 2. 编译验证

```bash
# 编译并验证
python scripts/mt5_compile.py WaiTrade2/WaiTrade_OB

# 检查输出
# 必须: 0 errors, 0 warnings
```

**检查清单：**
- [ ] 编译无错误无警告
- [ ] `.ex5` 文件时间戳更新

#### 3. 回测验证

**必须做的事：**

```bash
# 正确做法 —— Period 自动根据 bar_tf 设置
python scripts/mt5_cli_backtest.py --background --brief \
  --strategy <策略名> --symbol <品种> --days 720

# 分月验证（确保每月都能盈利或至少不崩）
python scripts/mt5_cli_backtest.py --background --brief \
  --strategy <策略名> --symbol <品种> \
  --from 2024.06.01 --to 2024.07.01
```

**回测检查清单：**
- [ ] **Period 已确认匹配 Live TF**（检查 INI 输出或报告头部）
- [ ] 720 天长周期回测完成，Model 4 / Real Ticks
- [ ] 每月独立回测，关注最近 6 个月的退化趋势
- [ ] WR > 80% 的结果必须查成交假设（可能是模型幻觉）
- [ ] 负余额月数记录在案（策略局限性文档）
- [ ] 回测资金 = Live 实际资金（默认 $200）

#### 4. 对比审计

```bash
# 生成交易摘要
python scripts/backtest_digest.py --report results/backtest/<策略>_<日期>_<日期>.txt --brief

# 导出交易明细
python scripts/backtest_digest.py --report results/backtest/<策略>_<日期>_<日期>.txt --export-csv

# 聚类分析
python scripts/trade_cluster_summary.py --csv results/backtest/<策略>_<日期>_<日期>.trades.csv --top 8
```

**对比检查清单：**
- [ ] 新版本 vs 旧版本：胜率、盈亏比、净 R、终值余额的对比表
- [ ] 近 6 个月逐月对比（识别是否只在特定行情下优化）
- [ ] 最大回撤对比
- [ ] 日均交易次数变化（是否过度交易或过度保守）

#### 5. 部署上线

**部署前确认清单：**

```
□ EA 编译完成（0 errors, 0 warnings）
□ 720 天回测通过（Model 4, Real Ticks）
□ .set 文件已通过 yaml_to_set.py 生成
□ .set 文件位于 MT5 可访问路径
□ startup.ini 指向正确的 .set 文件名
□ Magic Number 唯一（不与任何已部署策略冲突）
□ 策略版本号已更新，可区分新旧版本
□ Live 账户余额匹配回测资金
□ 多实例部署：terminal64.exe 已独立复制到 portable 目录
□ 入场诊断日志已启用（或明确记录关闭原因）
```

**部署步骤：**
1. 编译 `.set` 文件：`python scripts/yaml_to_set.py --strategy <策略名>`
2. 复制 `.set` 到 portable 目录的 `MQL5/Presets/`
3. 更新 `startup.ini` 中的 `ExpertParameters=<策略名>.set`
4. 启动 EA 后 **立即检查 EA 日志**：
   - 确认 `InpVersion` 匹配预期
   - 确认 `bar_tf` 匹配预期
   - 确认没有 `.set` 加载错误
5. 等待 5 分钟，确认心跳正常（`HEARTBEAT` 日志）
6. 记录部署审计文档到 `results/live/`

**禁止的操作：**
- ❌ 在 Live 上热替换 `.set`（不同版本可能共享 OB 缓存导致行为异常）
- ❌ 同时跑两个不同版本的同一策略（即使 Magic 不同）
- ❌ 部署没有 720 天回测验证的策略
- ❌ 在 $200 账户上跑 `max_lot_size >= 1.0` 或 `max_pos_mult >= 50` 的策略

#### 6. 复盘记录

每次部署后必须在 `research/notes/` 下记录：

```markdown
# YYYY-MM-DD_<策略名>_<事件>.md

## 部署参数
- 策略版本/Magic
- 品种/TF
- 风险参数

## 部署验证
- 编译状态
- 回测摘要（720d 终值、WR、PF）
- .set/版本一致性检查

## 异常记录
- （如有）

## 后续观察
- （24h/7d/30d 检查点）
```

---

## 三、参数安全边界

### Live $200 账户强制上限

| 参数 | 上限 | 原因 |
|------|:---:|------|
| `max_lot_size` | **0.1** | $200 账户 0.1 手 XAU ≈ $450 风险（已经很大） |
| `max_pos_mult` | **5.0** | 防止深度入场 boost 导致仓位失控 |
| `max_concurrent` | **5** | 同时持仓不超过 5 单 |
| `max_entries_per_ob` | **5** | 同一 OB 最多 5 次入场 |
| `ob_reentry_cooldown_min` | **≥3** | 至少 3 分钟冷却 |
| `cooldown_bars` | **≥1** | 至少 1 根 K 线全局冷却 |

### 策略分级标准

| 等级 | max_lot | max_concurrent | max_entries_per_ob | 适用场景 |
|------|:---:|:---:|:---:|------|
| 🔴 裸奔 | 5.0 | 14 | 20 | **禁止用于 Live** |
| 🟡 激进 | 0.5 | 5 | 5 | 已验证的历史强月 |
| 🟢 标准 | 0.1 | 3 | 3 | QS2/QS-defensive 级别 |
| 🔵 保守 | 0.05 | 2 | 2 | 新策略试运行 |

### 诊断日志要求

Live 部署必须开启：
- `InpEnableEntryDebug=true` — 入场信号跳过原因
- 不需要开启 `InpEnableExitDebug=true`（日志量太大，仅调试时用）

---

## 四、回测纪律

### TF 匹配规则（铁律）

> **回测使用的 BarTF 必须与 Live EA 的 `InpBarTF` 一致。**
>
> 回测脚本通过 `bar_period_min`（或 `bar_tf`）→ `Period=M{n}` 自动设置。
> 绝不能手动指定 `period` 覆盖策略的 `InpBarTF`。

**验证方法：** 回测完成后检查报告头部或 INI 文件中的 `Period=` 是否匹配策略 `.set` 中的 `InpBarTF`。

### 其他纪律

- 每季度跑一轮 720 天长周期回测，建立趋势线
- 关注最近 3 个月的胜率/PF 退化趋势
- BTC 和 XAU 分开调参（尺度不同）
- 不信任 Model 0 结果（Every tick = 幻觉）
- 负余额解析必须支持负号

---

## 五、Live 部署架构规范

### Portable 终端部署

```
temp/mt5_portable_<组合名>/
├── <腿1>/
│   ├── terminal64.exe        # 每个 portable 独立复制
│   ├── <启动配置>.ini
│   └── MQL5/
│       ├── Presets/<策略>.set
│       └── Logs/
├── <腿2>/
│   ├── terminal64.exe        # 每个 portable 独立复制
│   └── ...
└── portfolio_manifest.yaml
```

### 部署后即时验证

启动 EA 后 **5 分钟内必须确认**：

```text
✅ InpVersion 匹配预期（检查 EA 启动日志）
✅ bar_tf 匹配预期（检查 HEARTBEAT 中的 PERIOD_M{n}）
✅ 无 .set 加载错误
✅ Magic Number 唯一
✅ HEARTBEAT 正常出现（每 60 分钟一次）
✅ ob > 0（至少能检测到订单块结构）
```

---

## 六、异常处理手册

| 异常 | 处理 |
|------|------|
| .set 加载失败（MT5 错误码 2） | 检查文件路径，复制到 portable Presets 目录，重新同步 |
| EA 跑默认参数 | 立即停止，确认 .set 文件名和路径正确后重启 |
| WR > 80% | 怀疑数据/模型问题，用 Real Ticks 重跑 |
| 连续亏损 > 月止损线 | 策略自动停止新开仓（预期行为），检查是否需要调整止损阈值 |
| ZD/QS 一腿长期无 OB | 检查行情是否不适合该腿，考虑调整 OB 检测参数 |
| 同一 OB 连续重入 | 检查 `max_entries_per_ob` 和 `ob_reentry_cooldown_min` 是否生效 |

---

## 七、版本号规范

```
V<大版本><小版本>-<策略名>-<变体>

示例:
  V11XAU-QS           — 基础趋势腿
  V11XAU-QS2          — QS 防御版（DTP + 冷却 + 金字塔）
  V11XAU-ZD           — 基础振荡腿
  V11XAU-QS-DEFENSIVE — 全面防御版
  V11XAU-QS-HOLD-R1   — Hold 变体 R1

规则:
  - 大版本 = EA 架构代数（V11 = 当前第 11 代）
  - 策略名 = XAU/BTC/CRY 等品种标识 + QS/ZD/FAGE 等策略类型
  - 变体 = 参数变体的简短描述（HOLD/DEF/ULTRA 等）
  - 版本号必须在 .set 文件、strategies.yaml、EA 日志中一致
```

---

## 八、自动化检查脚本（待实现）

理想状态下，部署前应运行：

```bash
# 策略一致性检查（待开发）
python scripts/check_strategy_consistency.py --strategy <策略名>
# 检查:
#   ✅ bar_tf 在 strategies.yaml / .set / Config.mqh 中一致
#   ✅ Magic Number 唯一
#   ✅ 参数不超出安全边界
#   ✅ FLAT_MAP 覆盖所有 YAML key

# Live 部署前安全检查（待开发）
python scripts/pre_deploy_check.py --strategy <策略名> --balance 200
```

---

*本规范基于 2026-06-02 Live 审计发现制定，如有新问题发现应持续更新。*
