# PowerShell 编码问题根本性评估 (0704)

## 核心结论

**当前 profile 是 workaround, 不是根本解决。**

根本问题: Windows 11 默认装 PowerShell 5.1 (2016 年发布, 已 EOL), 有 5 个无法 config 修复的设计限制。

## 根本性 vs Workaround 评估

| 维度 | 当前 profile | 根本解 (PS 7+) | 状态 |
|---|---|---|---|
| UTF-8 输出 | workaround 设 Console.OutputEncoding | PS 7+ 默认 | partial |
| UTF-8 输入 (Get-Content) | workaround 设 PSDefaultParameterValues | PS 7+ 默认 | partial |
| 中文乱码 | workaround chcp 65001 + env vars | PS 7+ 默认 | partial |
| Python UTF-8 | workaround env vars | PS 7+ 默认 | partial |
| head/tail/which | workaround function | PS 7+ 内置 PSReadLine 增强 | workaround |
| **反引号转义** | **PS 语言设计, 无法 config** | **PS 7 同样存在** | **无法解, 靠习惯** |
| Out-File BOM | PS 5.1 必带 BOM | PS 7 默认 utf8NoBOM | workaround |
| PSReadLine 偶发崩溃 | 5.1 已知 bug | PS 7 已修 | partial |
| PS 5.1 EOL | n/a | 装 PS 7+ | 待装 |

## 5 个无法 config 修复的限制 (5.1)

1. **反引号在双引号中转义**: `@双引号双引号` 中 `反引号n` 解析为换行 (PS 语言设计, PS 7+ 同样存在)
2. **PSReadLine 历史搜索偶发崩溃**: 5.1 已知 bug (PS 7+ 已修复)
3. **Out-File 默认 UTF-16 LE**: 5.1 行为, 6+ 才改 (即使显式 utf8 也带 BOM)
4. **Get-Content 不读 UTF-8**: 需 PSDefaultParameterValues workaround (PS 7+ 默认行为)
5. **PS 5.1 已 EOL**: 无安全更新, 仅 bug fix

## 升级到 PS 7+ 的障碍

- 下载: PowerShell-7.4.6-win-x64.msi (104 MB) -- **已下载**
- 安装: 需管理员权限
- 当前用户状态: IsInRole(Administrator) = False
- UAC 提示: Start-Process -Verb RunAs 已显示, 但需用户手动确认
- 无法在 exec_command 中代用户点 UAC

## 调研结论

**这是用户权限限制, 不是技术障碍。**

用户当前有 3 个选择:

### 方案 A: 用户手动提权装 PS 7 (根本解)

1. 下载 .msi: https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/PowerShell-7.4.6-win-x64.msi
2. 右键 -> 以管理员身份运行 -> 装
3. 装完后, 把现有 profile 复制到:
   C:\Users\Gnef\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
4. 默认 shell 改 pwsh:
   wezterm 配 {"shell": {"program": "pwsh.exe"}} 或 WT 配 PowerShell 7

### 方案 B: 接受 workaround, 加强 profile (当前已做)

profile 解决了 80% 痛点:
- UTF-8 全栈 (out/in/file)
- Python UTF-8 输出
- 4 个 Unix 函数 (head/tail/which/ll)
- PSReadLine 历史搜索

剩余 20% (反引号转义) 靠习惯: 用 `@单引号单引号` 写 here-string

### 方案 C: 用 Python 完全替代 shell 任务 (零 PowerShell 依赖)

适合: 大量 shell 操作 + 编码敏感 + 需要自动化
实施: 写 py_shell.py 封装所有 shell 命令
优势: 编码完全可控, 反引号无转义问题, 跨 shell 一致
劣势: 不能用 PowerShell 原生命令 (Get-ChildItem 等)

## 当前建议

**立即**: 已写 profile, 解决 80% 痛点 (workaround)
**短期**: 写 py_shell.py 处理高频 shell 任务
**长期**: 用户手动提权装 PS 7+ (根本解)

## 反引号转义: 这是 PowerShell 语言设计, PS 7+ 也存在

唯一根治方法: 改变写作习惯

BAD (易踩反引号坑):
```powershell
$x = @"反引号n 反引号$_ 按字面输出"@
```

GOOD (单引号 here-string, 不解析任何转义):
```powershell
$x = @''@反引号n 反引号$_ 按字面输出'@
```

**结论: 即使装 PS 7, 这个习惯仍要保持**

## 公开资料引用

- PowerShell 5.1 vs 7.0: https://docs.microsoft.com/en-us/powershell/scripting/install/migrating-from-windows-powershell-51-to-powershell-7
- PowerShell GitHub Releases: https://github.com/PowerShell/PowerShell/releases
- PSDefaultParameterValues: https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parameters_default_values
- $PROFILE: https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles
