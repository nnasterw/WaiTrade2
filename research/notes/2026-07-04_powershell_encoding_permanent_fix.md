# Windows PowerShell 编码/转义问题一次性解决 (0704 调研)

## 背景

多次会话反复遇到 PowerShell 编码/转义问题:
1. Write-Output 中文显示乱码
2. 反引号 here-string @双引号 中 反引号n 解析为换行 (破坏 0704 笔记)
3. head / tail / which / grep 等 Unix 工具不可用
4. Python 子进程输出乱码

每次会话都需重复设置 [Console]::OutputEncoding = UTF8 + chcp 65001 + PYTHONIOENCODING=utf-8

## 调研结论

可以一次性解决。 方案: 在 PROFILE 中配置 4 项设置。

### 一次性方案: PowerShell profile

文件位置: C:\Users\Gnef\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1

配置内容:
1. UTF-8 输出 + 输入 (PS 5.1 必须显式设 Get-Content:Encoding=utf8)
2. Python 强制 UTF-8 (PYTHONIOENCODING=utf-8 + PYTHONUTF8=1)
3. Unix 风格函数别名 (head/tail/which/ll/la)
4. PSReadLine 增强 (历史搜索)

生效方式: PowerShell 启动时自动加载, 新会话立即生效。

### 4 个解决方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|
| H1: PowerShell 7+ (pwsh) | 单点解决 5.1 限制 | 需安装 50MB+ | 3 |
| H2: 单引号 here-string | 立即生效 0 安装 | 仅解决转义 | 4 |
| H3: Profile 配置 | 一次性自动加载 | 仍受 5.1 限制 | 4 |
| H4: Python 替代 shell | 编码可控 | 脚本复杂 | 2 |
| H5: 装 Git Bash | shell 兼容 | PowerShell 不可用 | 2 |

采用: H2 + H3 组合 (profile + 单引号 here-string 习惯)
未来: 安装 pwsh (PowerShell 7) 进一步消除 5.1 限制

### 关键技术细节

Windows PowerShell 5.1 已知限制:
- Get-Content 默认不读 UTF-8 (即使 Console 已设 UTF-8)
  必须: PSDefaultParameterValues Get-Content:Encoding = utf8
- Out-File 5.1 默认 UTF-16 LE
  5.1: Out-File -Encoding utf8 (带 BOM)
  6+: 默认 utf8NoBOM
- 反引号 在双引号字符串中转义:
  反引号n=LF, 反引号r=CR, 反引号t=TAB, 双反引号=字面反引号
- @双引号双引号@ 双引号 here-string 解析 $ 和 反引号
- @单引号单引号@ 单引号 here-string 不解析任何转义 (推荐用)

chcp 65001 副作用:
- 部分 cmd.exe 命令输出异常 (如 findstr)
- Python 3.6 之前在 chcp 65001 下崩溃
- 现已普遍支持, 但仍需 PYTHONIOENCODING=utf-8 作为保险

## 实施记录

- 0704: 创建 profile 脚本 (1863 bytes)
- 0704: 验证 head/tail/which/ll 全部工作
- 0704: 验证 UTF-8 中文输入输出正常
- 0704: 验证 Python 中文输出正常

## 使用约定

写 here-string 必用单引号:
```powershell
$content = @''@ 不解析任何转义
'@
```

读 UTF-8 文件无需 -Encoding:
```powershell
Get-Content file.txt   # 自动 UTF-8 (profile 默认值)
```

## 已知局限

1. 5.1 PSReadLine 历史搜索偶发崩溃 - 升级 PS 7+ 可解
2. head/tail 处理超大型文件 (>10MB) 较慢 - 用 Get-Content -ReadCount 1000
3. PowerShell 5.1 不再更新 - 长期方案迁移 PS 7+

## 升级建议

下一步: 安装 PowerShell 7 (pwsh)
- 下载: https://github.com/PowerShell/PowerShell/releases
- 命令: winget install Microsoft.PowerShell
- 验证: pwsh -Command $PSVersionTable.PSVersion
- 迁移: profile 复制到 C:\Users\Gnef\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
