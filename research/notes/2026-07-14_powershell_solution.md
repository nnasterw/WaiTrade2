# Powershell 解决方案最终报告 (2026-07-14)

## 实测数据 (3 次平均, 冷启动)

| shell + cmd | avg | min | 备注 |
|---|---:|---:|---|
| `cmd /c echo 1` | 64ms | 36ms | 最快 |
| `bash -c "echo 1"` (git bash) | 43ms | 38ms | 同等最快 |
| `powershell -NoProfile -Command "1+1"` | 306ms | 257ms | PS5 |
| `pwsh -NoProfile -Command "1+1"` | 558ms | 413ms | PS7 慢 80% |
| `pwsh -NoProfile -NoExit -Command "exit 0"` | 931ms | 833ms | 加 -NoExit 更慢 |
| `cdx-shell.cmd python -V` (我自己加的包装器) | 1258ms | 1018ms | **20x cmd**, 错误方案 |

**关键发现：pwsh 7 在 Windows 上比 PS5 慢 80%**。之前的假设错误。

## 之前"参数解析失败"真实原因

不是 powershell 系统性问题，而是**单次特殊情况**：
- powershell 5 解析单引号时：`$env:MT5_HOME='value'` 中 `=` 被吞
- powershell 7 解析双引号时：`"=value"` 变成 "=value"
- **真解决方案**用 `;` 分隔多个语句，避免在字符串中嵌 `=`

## 最优方案

### 使用 powershell 5 (默认, 已可用)
- 启动 ~300ms - 可接受
- 所有当前 case 都能跑
- **无需升级 pwsh** (升级反而慢)

### 标准化命令模板 (写到 AGENTS.md 给 agent 用)
```
# 模板: 多环境变量 + 命令链
$env:VAR1='val1'; $env:VAR2='val2'; $env:PYTHONIOENCODING='utf-8'
python 'D:\path\to\tools.py' --arg1 val1 --arg2 val2 2>&1 | Select-Object -First 10
```

### 关键模式
- **`;` 分隔**多环境变量赋值 (不用 `&&`/`||` — powershell 不支持)
- **`2>&1 | Out-Null`** 抑制 stderr (避免 token 浪费)
- **`-NoProfile`** powershell 显式跳过 profile (避免读 .ps1 拖慢)
- **MT5 portable 启动 ~30-60s** 比 powershell 启动大 100x, 不是 shell 问题

## 已删除

- `C:\Users\Gnef\bin\cdx-shell.ps1` (包装器开销过大, 20x cmd)
- `C:\Users\Gnef\bin\cdx-shell.cmd` (同)

## 保留

- powershell 5 (默认) 用于日常 shell
- pwsh 7 用于更复杂场景 (脚本编辑, 性能不重要)
- bash (git bash) 用于 unix-style 短命令
- cmd 用于最快启动

## Agent 编写复杂命令建议

1. **简单命令** → powershell 5, 不需特别处理
2. **多行复杂命令** → here-string `@'...'@` 或 stdin 重定向
3. **环境变量链** → 用 `;` 分隔, 不用 `&&` / `||`
4. **长 python 脚本** → 写到 `.py` 文件, 然后 `python file.py` 执行
5. **回测工具链 (MT5)** → 用 `$env:` + `2>&1` 收集所有输出
6. **避免重复执行同一命令** → 每次重发消耗 ~50ms + 重复 output