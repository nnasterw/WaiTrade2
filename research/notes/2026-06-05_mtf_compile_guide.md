# MTF 框架编译指南

日期: 2026-06-05

## 踩坑记录

### 坑1: metaeditor64.exe /compile 是语法检查，不生成 .ex5
- 命令 `metaeditor64.exe /compile:file.mq5` 只做语法检查 (0 errors, 0 warnings)
- **不会输出 .ex5 文件**
- 在某些情况下甚至会**删除已有的 .ex5**
- 必须用 MetaEditor GUI (F7) 完成编译

### 坑2: 终端 ID 混淆 — D0E8209F vs 2A77830F vs portable
- 系统中有 16 个 MT5 终端实例 (16 个不同的 terminal ID)
- `D0E8209F77C8CF37AD8BF550E51FF075` — 脚本中配置的 ID，但有 .mq5 无 .ex5
- `2A77830F8CA47491ACE42E08AB980E48` — 最新 .ex5 在此，但被 metaeditor 删除了
- `temp/mt5_portable_bt/` — **正确的回测终端**（独立 portable，不影响 Live）
- 回测应使用 portable BT 实例，而非 Program Files 的 MT5

### 坑3: 源文件同步目标
- 必须同时同步到 portable BT 实例和 Program Files 的 MQL5 目录
- portable BT 路径: `temp/mt5_portable_bt/MQL5/`
- 编译后 .ex5 在 portable BT 中

## 编译步骤 (命令行 — 已验证可用)

### 方法: PowerShell Start-Process (推荐)

```powershell
$bt = "D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt"
$p = Start-Process -FilePath "$bt\metaeditor64.exe" `
  -ArgumentList "/compile:`"$bt\MQL5\Experts\WaiTrade2\WaiTrade_OB.mq5`"",
                "/inc:`"$bt\MQL5`"",
                "/log:`"$bt\compile_mtf.log`"" `
  -Wait -PassThru
Write-Host "Exit: $($p.ExitCode)"
ls "$bt\MQL5\Experts\WaiTrade2\WaiTrade_OB.ex5"
```

### 关键点
- 必须用 `/inc:` 指定 MQL5 目录，否则 include 解析失败
- 路径不能有空格
- PowerShell 的 Start-Process 比 cmd.exe 更可靠
- 编译成功标志: `Result: 0 errors, 0 warnings` + .ex5 文件生成

### 方法: MetaEditor GUI (备用)
1. 打开 `temp/mt5_portable_bt/metaeditor64.exe`
2. File → Open → `WaiTrade_OB.mq5`
3. F7 编译

## 回测命令 (使用 portable BT)

```bash
# 1. 先同步源文件到 portable BT
BT=temp/mt5_portable_bt
cp mql5/Include/WaiTrade2/MTFContext.mqh $BT/MQL5/Include/WaiTrade2/
cp mql5/Include/WaiTrade2/Config.mqh $BT/MQL5/Include/WaiTrade2/
cp mql5/Include/WaiTrade2/SignalEngine.mqh $BT/MQL5/Include/WaiTrade2/
cp mql5/Experts/WaiTrade2/WaiTrade_OB.mq5 $BT/MQL5/Experts/WaiTrade2/

# 2. 生成含MTF参数的.set
python scripts/yaml_to_set.py v11xau-qs3 -o mql5/Presets/v11xau-qs3-mtf.set
cp mql5/Presets/v11xau-qs3-mtf.set $BT/MQL5/Profiles/Tester/v11xau-qs3.set

# 3. 编译 (需在 MetaEditor GUI 中按 F7)

# 4. Phase 1: MTF=OFF 回测
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --days 7

# 5. Phase 2: MTF=ON 回测 (修改 .set: InpEnableMTF=true 后)
python scripts/mt5_backtest_win.py --strategy v11xau-qs3 --symbol XAUUSDm --days 7
```

## 文件清单

| 文件 | 状态 | 说明 |
|------|:---:|------|
| MTFContext.mqh | 已创建 | ~250行, 多周期OB检测+规则引擎 |
| Config.mqh | 已修改 | +11 MTF参数 |
| WaiTrade_OB.mq5 | 已修改 | +include +UpdateMTFContext +RecordEntryDirection |
| SignalEngine.mqh | 已修改 | +AdjustPosMultByMTF 裁决入口 |
| yaml_to_set.py | 已修改 | +11 FLAT_MAP映射 |
| strategies.yaml | 已修改 | +11 默认值 |
| .ex5 | 待编译 | 需 GUI MetaEditor 编译 |
