# Windows vs Wine 回测脚本差异审计

日期: 2026-05-19  
状态: 审计完成 + 冷启动已修复

## 审计范围

| 文件 | 角色 |
|------|------|
| `scripts/mt5_cli_backtest.py` | Wine/macOS 回测运行器 |
| `scripts/mt5_backtest_win.py` | Windows 原生回测运行器 |
| `scripts/mt5_common.py` | 共享纯函数库 |
| `scripts/mt5_compile.py` | EA编译器(Wine only) |
| `scripts/mt5_live_runner.py` | Live部署(Wine only) |

---

## 差异分类

### A. 已修复 (commit 859e925)

| 差异 | 风险 | 修复方式 |
|------|------|----------|
| Windows版缺少`kill_mt5()` | **高** — 缓存复用导致结果失真 | 新增`kill_mt5()`用`taskkill /F /IM` |
| Windows版缺少`clear_tester_cache()` | **高** — 同上 | 新增,清空`MT5_TESTER_DIR/cache/` |
| `run_mt5()`启动前无冷启动序列 | **高** — 批量回测核心风险 | 调用顺序: kill → 清缓存 → Popen |

### B. 有意保留的差异 (合理不一致)

| 差异 | Wine版 | Windows版 | 保留原因 |
|------|--------|-----------|----------|
| INI `[Common]`段 | 有(Login/Server/Proxy) | 无 | Windows通过GUI登录,不需INI注入账号 |
| `Currency`字段 | 无 | 有 | Windows版更完整,Wine版遗漏但MT5有默认值 |
| 进程管理命令 | `pkill`(Unix) | `taskkill`(Win32) | 平台差异,行为等效 |
| 路径来源 | 硬编码WINEPREFIX | `MT5_HOME`/`MT5_DATA`环境变量 | Windows版设计更灵活,Wine路径固定 |
| `patch_terminal_ini_dates()` | 有 | 无 | Wine下MT5忽略INI日期的workaround,Windows原生未发现同问题 |
| INI写入位置 | 两处(bt/ + config/) | 一处(Tester/) | Wine需要两份是历史实验遗留 |

### C. 键名差异 (功能等效)

| 字段 | Wine版 | Windows版 | MT5行为 |
|------|--------|-----------|----------|
| 起始日期 | `DateFrom=` | `FromDate=` | 两种都接受 |
| 结束日期 | `DateTo=` | `ToDate=` | 两种都接受 |
| 报告路径 | `Report=C:\bt\reports\name` (绝对) | `Report=name` (相对) | 都能工作 |

> 注: `FromDate`/`ToDate`是MT5官方文档格式,Windows版更标准

### D. 成功判断逻辑差异

| | Wine版 | Windows版 |
|-|--------|----------|
| 判断方式 | 非超时即成功(`return True`) | 退出码判断(`returncode == 0`) |
| 风险 | MT5崩溃(非超时退出)也报"成功" | 更严格,崩溃会返回False |
| 状态 | Wine版逻辑更弱,但不影响实际使用(崩溃时日志也为空,后续解析会报警告) |

### E. Windows 缺失的能力模块

| 能力 | macOS Wine | Windows | 是否需要补全 |
|------|:---:|:---:|------|
| EA编译 | `mt5_compile.py` | ❌ | **低优先** — MetaEditor IDE够用,且实现仅需20行 |
| Live部署 | `mt5_live_runner.py` | ❌ | **中优先** — 等Windows Live需求明确时再做 |
| 进度打点 | ❌ | 每10s输出`.` | Wine版可选添加(UX改进) |

---

## 架构对比图

```
┌────────────────────────────────────────────────────────────────────────┐
│                  config/strategies.yaml (唯一真相源)                    │
└─────────────────┬──────────────────────────────────┬───────────────────┘
                  │                                  │
            ┌─────▼─────────┐                 ┌──────▼──────────┐
            │ yaml_to_set.py │                 │ mt5_common.py   │
            │ (参数转换)      │                 │ (纯函数库)      │
            └─────┬──────┬──┘                 └──────┬──────────┘
                  │      │                           │
     ┌────────────▼──┐  ┌▼───────────────────────────▼──┐
     │  Wine回测      │  │       Windows回测              │
     │  cli_backtest  │  │       backtest_win             │
     │                │  │                                │
     │ ✅ kill(pkill)  │  │ ✅ kill(taskkill) [已修复]      │
     │ ✅ clear_cache  │  │ ✅ clear_cache    [已修复]      │
     │ ✅ patch_dates  │  │ ❌ (不需要)                     │
     │ ✅ INI双写      │  │ ✅ INI单写                      │
     │ ⚠️ 成功=非超时  │  │ ✅ 成功=returncode 0           │
     └────────────────┘  └──────────────────────────────┘

     ┌────────────────┐  ┌──────────────────────────────┐
     │ mt5_compile    │  │       (无对应)                 │
     │ (Wine编译)     │  │ MetaEditor IDE手动编译        │
     └────────────────┘  └──────────────────────────────┘

     ┌────────────────┐  ┌──────────────────────────────┐
     │ mt5_live_runner│  │       (无对应)                 │
     │ (Wine Live)    │  │ Windows需/config:+[StartUp]   │
     └────────────────┘  └──────────────────────────────┘
```

---

## 潜在风险监控清单

### 需持续关注

1. **Windows日期缓存问题** — 如果发现Windows版回测日期不对(报告显示的日期范围与指定不一致),需要移植`patch_terminal_ini_dates()`。当前无证据表明Windows有此问题。

2. **Wine版成功判断** — 如果MT5 Wine进程崩溃(非超时)但被当作成功,会读到空日志或上次日志。当前通过`parse_agent_log()`返回None + `calc_stats(None)`返回None来兜底,不会产生虚假成功结果。

3. **共享函数diverge** — 两个版本各自实现了`generate_ini()`、`run_mt5()`、`parse_agent_log()`。如果未来改了日志格式或INI需求,必须两边同步修改。考虑未来是否应提取共享基类或更多纯函数到`mt5_common.py`。

### 已封闭的风险

- ✅ 批量回测缓存复用 → 冷启动机制已添加
- ✅ `expert_ex5_path()`签名不同但结果等价 → 接受差异,函数内部自洽

---

## 测试覆盖

| 文件 | 测试 | 覆盖范围 |
|------|------|----------|
| `tests/test_mt5_common.py` | 48个 | 日志解析/统计/策略解析/报告/参数映射 |
| `tests/test_mt5_backtest_win.py` | 18个 | INI生成/kill/cache/run流程/路径计算 |
| Wine版测试 | ❌ 无 | generate_ini/patch_dates/run_mt5 无测试 |

### 下一步测试建议

- Wine版`generate_ini()`应有同等INI内容测试(验证键名、结构)
- Wine版`patch_terminal_ini_dates()`应有单元测试(regex替换正确性)
- 两版`run_backtest()`的集成测试需要mock MT5进程(目前无法在CI中运行真实回测)

---

## 决策记录

| 决策 | 理由 | 日期 |
|------|------|------|
| Windows不移植`patch_terminal_ini_dates` | 无证据Windows有日期缓存问题,移植增加复杂度 | 2026-05-19 |
| Windows不补全编译脚本 | MetaEditor IDE可用,实现仅20行,等有CI需求再做 | 2026-05-19 |
| Windows不补全Live部署 | Windows Live需求未明确,且方案不同(需/config:+[StartUp]) | 2026-05-19 |
| 保留键名差异(FromDate vs DateFrom) | 两种MT5都接受,Windows版用官方格式更标准 | 2026-05-19 |
| 不统一INI中`[Common]`段 | 登录方式不同,Windows靠GUI不靠INI | 2026-05-19 |
