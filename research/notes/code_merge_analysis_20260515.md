# WaiTrade2 最新代码合并分析

**日期**: 2026-05-15  
**来源**: WaiTrade2 (commit becf309, dc782ef, 14bb1e3, af0b68b, 1848339, b8f4cb3)
**目标**: WaiTrade (Python Live 交易)

---

## 一、变更摘要

| 变更 | 类型 | 对 Live 影响 | 是否合并 |
|------|------|-------------|----------|
| v9.8 四维框架 (EA) | EA 重写 | 仅 EA 端，Python 不支持 | ❌ 需 EA 编译 |
| v97b ExpX 定版 | 策略 | 依赖 v9.8 参数 | ❌ Python 无对应实现 |
| v96b_live 调优 | 策略 | 基础参数，Python 可用 | ✅ 可合并 |
| v97a 定义更新 | 策略 | BElock0.20 + bounce40% + DTP20% | ⚠️ 与当前 WaiTrade v97a 冲突 |
| defaults 新增 spread_floor | 参数 | 新参数 | ✅ 可合并 |
| defaults bars: 300 | 参数 | 减少历史 bar | ⚠️ 需评估 |
| Model 4 Real Ticks | 回测 | 不适用 Live | - |
| 新 MQL5 模块 | EA 代码 | 不适用 Python Live | - |
| mql5_original/ | EA 备份 | 不适用 | - |

---

## 二、WaiTrade 与 WaiTrade2 v97a 参数冲突

| 参数 | WaiTrade (当前 live) | WaiTrade2 (远程) | 差异 |
|------|---------------------|-------------------|------|
| breakeven_r | 1.0 | 0.3 | WaiTrade 更保守 |
| breakeven_lock_r | 0.2 | 0.20 | 相同 |
| bounce_pct | 0.30 | 0.40 | WaiTrade2 更严格 |
| dtp_trigger_r | 3.0 | 2.0 | WaiTrade 更晚 |
| dtp_retrace | 0.35 | 0.20 | WaiTrade2 更紧 |
| trail L1 | 1.5R→0.5R | (继承默认 1.0R→0.2R) | 完全不同 |
| require_double_touch | false | false | 相同 |
| min_risk_spread_ratio | 5.0 | (继承默认 3.0) | WaiTrade 更严 |
| time_exit_bars | 20 | (继承默认 999) | WaiTrade 有时间退出 |
| boost_in_1h_ob | 1.0 | 1.0 | 相同 |

**结论**: WaiTrade 的 v97a（当前正在 live 运行）和 WaiTrade2 的 v97a 是两个完全不同的策略版本。需要协调统一。

---

## 三、v96b_live 调优参数（建议合并）

| 参数 | v96b 原始 | v96b_live | 改进点 |
|------|----------|-----------|--------|
| max_entry_offset_r | 1.5 | 0.8 | 收紧入场偏移，减少追价 |
| breakeven_r | 0.2 | 0.5 | 晚保本，给行情空间 |
| breakeven_lock_r | 0.05 | 0.15 | 保本锁更多利润 |
| max_concurrent | 5 | 2 | 控制并发，避免集中亏损 |

---

## 四、建议合并方案

### 立即合并（P0）
1. **v96b_live 参数**作为新 profile 添加到 WaiTrade
2. **同步 defaults**中的 spread_floor=0.0 到 WaiTrade

### 待协调（P1）
3. **统一 v97a 定义**: 当前 WaiTrade live 运行的 v97a 参数 vs WaiTrade2 的 v97a
   - 建议：WaiTrade 的 v97a 重命名为 v97a_live（避免冲突）
   - 或：将 WaiTrade2 的 v97a 参数同步到 WaiTrade

### 暂不合并（需 EA 升级）
4. v9.8 四维框架：需要 EA 重新编译，Python 端无对应实现
5. v97b ExpX 定版：依赖 enable_state_filter/enable_scoring 等 v9.8 参数

---

## 五、v97b ExpX 回测结果摘要

- 8笔/62.5%WR/2.64盈亏比/$221（起始 $200）
- 参数：score4+bounce60%+并发1+DTP3.0R+state_filter+decay_exit
- **当前唯一在 Real Ticks 下盈利的策略**
- 交易量太少（8笔），扩大样本是下一步方向
