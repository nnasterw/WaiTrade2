# Windows回测比Wine慢40倍诊断

日期: 2026-05-19  
现象: Wine/macOS XAU 180天 ≈ 3min，Windows XAU 180天 ≈ 2h（40x差异）

---

## 假设排序

### H1: 网络代理缺失 → Real Ticks下载极慢 [最可能 90%]

**核心证据**：

Wine版INI `generate_ini()` 生成：
```ini
[Common]
Login=277396794
Server=Exness-MT5Trial5
ProxyEnable=1
ProxyType=0
ProxyAddress=127.0.0.1:7897

[Tester]
...
```

Windows版INI `generate_ini()` 生成：
```ini
[Tester]
...
```

**没有 `[Common]` 段 = 没有代理注入。**

**机制**：Model 4 (Real Ticks) 要求MT5从broker服务器(Exness海外)下载逐tick历史数据。XAU 180天的tick数据量达数GB。

- Wine版：INI强制注入SOCKS5代理(127.0.0.1:7897=Clash) → 隧道连接Exness → 下载快
- Windows版：INI无代理 → 如果MT5 GUI也没配代理 → 直连海外 → 中国网络下极慢/超时/重连

**验证方法**：
1. Windows MT5 GUI: Tools → Options → Server → Enable proxy → SOCKS5 127.0.0.1:7897
2. 重跑同一个回测，计时
3. 预期：2h → ~3min

**代码层面修复**：Windows版`generate_ini()`也加入`[Common]`段。

---

### H2: Tick缓存被清空 → 每次重新下载 [叠加因素 60%]

刚添加的`clear_tester_cache()`会清空`MT5_TESTER_DIR/cache/`。如果tick历史数据也在此目录：

- 每次回测前清缓存 → 强制重新下载全部tick数据 → 在H1(无代理)条件下2h
- Wine版也清缓存，但有代理所以重新下载也只需几十秒

**MT5 Tester目录结构**：
```
Tester/
├── cache/          ← 回测结果缓存（我们清的是这个）
├── History/        ← tick历史数据（不应清理）
└── Agent-127.0.0.1-3000/
    └── logs/       ← 日志
```

`clear_tester_cache()`只清`cache/`子目录，不影响`History/`。所以如果tick数据在`History/`则不受影响。

但如果Windows MT5把tick数据也放在`cache/`（需实际验证目录内容），那每次清缓存=重新下载全部。

**验证方法**：
1. 在Windows上跑一次回测后，查看`cache/`和`History/`目录大小
2. 不清缓存再跑第二次同品种同日期，比较耗时

---

### H3: Windows杀毒实时扫描 [低概率 5%]

Windows Defender对`terminal64.exe`/`metatester64.exe`高频I/O实时扫描。

- tick模拟每秒百万次price计算 → 每次内存映射文件读取被拦截
- 影响量级：通常2-5x，不太可能造成40x

**验证方法**：MT5目录加入Defender排除列表后重测

---

### H4: Model值被GUI覆盖 [极低概率 2%]

类似Wine版的`patch_terminal_ini_dates()`问题 — Windows MT5可能忽略INI中的`Model=4`，使用GUI缓存的Model 0（Every Tick Exact，比Real Ticks更慢）。

**验证方法**：
1. 检查Agent日志第一行，显示实际使用的Model
2. 或回测完后看Tester窗口标题栏显示的Model

---

### H5: sleep(3)等待 [已排除 0%]

3s × 1次 = 仅增加3秒，不解释40x差异。

---

## 推荐修复顺序

### 立即验证（需要在Windows上操作）

1. **确认代理是否配置**：Windows MT5 → Tools → Options → Server → 查看proxy设置
2. **手动配代理后重测**：如果没配proxy，加上SOCKS5 127.0.0.1:7897后重跑
3. **检查Agent日志**：确认实际Model是否为4

### 代码修复（确认H1后）

在`mt5_backtest_win.py`的`generate_ini()`中加入`[Common]`段：

```python
# 当前Windows版只有 [Tester]，应改为：
ini_content = f"""; WaiTrade2 {strategy_name} / {symbol} 回测
[Common]
Login={login}
Server={server}
ProxyEnable={proxy_enable}
ProxyType={proxy_type}
ProxyAddress={proxy_address}

[Tester]
...
"""
```

这样Windows版INI结构与Wine版完全对齐，代理配置通过INI强制注入，不依赖GUI手动设置。

### 如果H2也成立

修改`clear_tester_cache()`策略：只清结果缓存，不清tick历史。需确认Windows上tick数据的实际存放路径。

---

## 性能预期（修复后）

| 条件 | Wine/macOS | Windows(修复前) | Windows(修复后预期) |
|------|-----------|----------------|--------------------|
| XAU 180天 Model 4 | ~3min | ~2h | ~3-5min |
| 瓶颈 | 无(代理+缓存) | 网络(无代理直连海外) | 应与Wine持平 |

如果修复代理后Windows仍比Wine慢很多（比如30min vs 3min），再排查H3(杀毒)和H4(Model覆盖)。
