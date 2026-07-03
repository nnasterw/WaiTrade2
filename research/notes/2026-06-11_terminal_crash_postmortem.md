# 回测终端事故报告 — 2026-06-11

## 事故时间线

| 时间 | 事件 |
|------|------|
| 10:47 | 最后一次成功回测 (BOS v1 30d, $76.35) |
| 11:02 | `smoke3.py` 执行 `rm -rf Tester/` 删除全部Tester目录 |
| 11:02 | 尝试从QS终端恢复 `bases/`——但QS正在运行, bases文件被锁定 |
| 11:02-16:00 | 反复尝试手工INI→terminal→失败("Optim not exist") |
| 15:57 | 删除mt5_portable_xau, 从QS克隆重建 |
| 16:00 | 新终端连接Exness成功但启动Live模式(因QS的startup.ini覆盖) |
| 16:05 | 停QS Live→用QS终端跑回测→同失败 |
| 16:09 | 发现C:盘安装终端也不可用 |

## 根因

**直接原因**: `smoke3.py` L13: `sh.rmtree(tdir)` 删除了 `Tester/` 全部内容。
`Tester/bases/Exness-MT5Trial5/history/XAUUSDm/*.hcs` 是Exness下载的tick历史缓存(数GB)。
删除后终端无法执行Model 4回测。

**深层原因**:
1. 脚本编写不规范——清缓存应该只清 `Tester/cache/`, 不是 `Tester/`
2. 恢复手段错误——从运行的QS终端拷贝bases(文件锁定/不完整)
3. 终端重建时遗漏了 `Tester/bases/` 在 `Tester/` 子目录而非终端根目录

## 教训

**铁律**: 
- 永远只删除 `Tester/cache/`, 不动 `Tester/bases/`
- 不做 `rm -rf Tester`——这等于删除MT5回测引擎的核心数据
- 回测脚本里不写破坏性删除操作

**恢复方案**:
1. 重启QS终端(恢复Live连接)
2. 让QS终端在线运行时, MT5自动从Exness重新下载XAUUSDm tick数据到Tester/bases/
3. 或者: 从备份恢复mt5_portable_xau (如果有git或备份)
4. 验证: 先跑1天Model 0回测→再跑Model 4
5. 长期: 保持一份 `Tester/bases/` 的备份

## 影响

- BOS Retest功能代码已完成但无法回测验证
- P1+P2最优参数已在事故前确认 ($2,610/-$126)
- 回测终端需重建后恢复验证能力
