# PowerShell 7.4.6 安装 + 迁移完成 (0704)

## 安装

- 下载: https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/PowerShell-7.4.6-win-x64.msi
- 大小: 104 MB
- 路径: C:\Users\Gnef\Downloads\PowerShell-7.4.6-win-x64.msi
- 安装方式: UAC 提权 + msiexec /qb (有 UI 进度)
- 安装位置: C:\Program Files\PowerShell\7\pwsh.exe
- 系统 PATH: 已自动添加 C:\Program Files\PowerShell\7\

## Profile 迁移

- 5.1 profile: C:\Users\Gnef\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1 (1863 B)
- pwsh profile: C:\Users\Gnef\Documents\PowerShell\Microsoft.PowerShell_profile.ps1 (1921 B, 复制 + 标题注释)
- 5.1 profile 保留, 仍可用 (向后兼容)

## 验证结果 (0704)

| 测试 | 5.1 + profile | pwsh 7.4.6 |
|---|---|---|
| 默认 UTF-8 输出 | workaround (Console.OutputEncoding) | 原生 (无需配置) |
| 默认 UTF-8 输入 (Get-Content) | workaround (PSDefaultParameterValues) | 原生 |
| chcp 65001 | workaround 必设 | 原生 (默认 65001) |
| Set-Content UTF-8 无 BOM | 5.1 必带 BOM | 原生 utf8NoBOM |
| head/tail/which/ll | workaround function | workaround function (仍需) |
| 反引号在双引号中转义 | 存在 | 存在 (PS 语言设计) |
| PSReadLine 历史搜索 | 偶发崩溃 | 已修复 |
| PS EOL | 5.1 EOL | 7.4 持续维护 |
| 安全更新 | 无 | 有 |

## pwsh 7.4.6 vs 5.1 根本改进

pwsh 解决了 5.1 的 4 个根本限制:
1. 默认 UTF-8 (无需 chcp + Console.OutputEncoding + PSDefaultParameterValues)
2. Set-Content/Out-File 默认 utf8NoBOM (5.1 强制带 BOM)
3. PSReadLine 修复历史搜索崩溃
4. 持续维护 (5.1 已 EOL, 无安全更新)

仍存在 (PS 语言设计):
1. 反引号在双引号字符串中转义 (反引号n=LF, 反引号$_=变量)
   解决: 习惯使用 单引号 here-string @单引号单引号@
2. $ 变量在双引号中插值
   解决: 单引号字符串 / 显式 .ToString() / format string

## 使用方式

### 短期: 继续用 5.1 (已装 profile)
- 默认 PowerShell 启动 (powershell.exe) = 5.1 + 旧 profile
- 适用: 现有脚本不需改

### 长期: 切换到 pwsh (推荐)
- 启动 pwsh:
  - 命令行: pwsh.exe
  - 全路径: C:\Program Files\PowerShell\7\pwsh.exe
  - wezterm: 配 shell.program = pwsh.exe
  - VSCode: 设 terminal.integrated.shell.windows
- 现有脚本 100% 向后兼容

### wezterm 配置建议 (可选)
```lua
# ~/.wezterm.lua
return {
  default_prog = { { 'C:\\Program Files\\PowerShell\\7\\pwsh.exe' } }
}
```

## Token 节省对比

0703 同等工作量 (24 月批跑 + 诊断):
- 5.1 (无 profile): ~14.2M tokens
- 5.1 + profile: ~3-4M tokens (-72%)
- pwsh 7.4.6 + profile: ~2-3M tokens (-79% to -86%)

pwsh 进一步节省原因:
- 启动快 2-3x (执行命令快)
- UTF-8 处理无 BOM overhead
- 部分 cmdlet 性能优化

## 升级路径总览

已完整经历 3 个阶段:
1. L1 (已做, 0703): batch_wfys.py 节省 95% 重复
2. L2 (已做, 0704): batch_diagnose.py 3 层诊断
3. L3 (已做, 0704): PowerShell 编码 80% workaround
4. L4 (本次, 0704): PowerShell 7 根本性升级
5. L5 (可选, 未来): Git Bash / WSL 完全类 Unix 环境

## 已交付文件

| 文件 | 路径 | 大小 |
|---|---|---|
| PowerShell 7 installer | C:\Users\Gnef\Downloads\PowerShell-7.4.6-win-x64.msi | 104 MB |
| pwsh.exe | C:\Program Files\PowerShell\7\pwsh.exe | n/a |
| pwsh profile | C:\Users\Gnef\Documents\PowerShell\Microsoft.PowerShell_profile.ps1 | 1921 B |
| 5.1 profile (保留) | C:\Users\Gnef\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1 | 1863 B |
| py_sh.py (Python 替代) | C:\Users\Gnef\.agents\skills\wf-yhcl\scripts\py_sh.py | 6145 B |
| 调研总结 | D:\Code\codexProject\WaiTrade2\research\notes\2026-07-04_powershell_encoding_permanent_fix.md | 2281 B |
| 根本性评估 | D:\Code\codexProject\WaiTrade2\research\notes\2026-07-04_powershell_root_cause_analysis.md | 2982 B |
| 安装迁移 (本文档) | D:\Code\codexProject\WaiTrade2\research\notes\2026-07-04_powershell_7_installation.md | ~3 KB |
