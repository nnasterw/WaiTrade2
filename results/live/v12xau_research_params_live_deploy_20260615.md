# v12 XAU 研究版参数 live 部署记录 - 2026-06-15

## 操作

用户明确确认: 解除 live 安全限制，使用研究版参数重启 XAU1 和 XAU2。

## 终端

- XAU1: `temp/mt5_portable_xau_v12/XAU1/terminal64.exe /portable /config:v12xau1_live_startup.ini`
- XAU2: `temp/mt5_portable_xau_v12/XAU2/terminal64.exe /portable /config:v12xau2_live_startup.ini`
- 账号: Exness-MT5Trial5 / 277656700
- 品种/周期: XAUUSDm / M1

## 部署 set

- XAU1: `temp/mt5_portable_xau_v12/XAU1/MQL5/Presets/v12xau1.set`
  - 来源: `temp/mt5_portable_bt/MQL5/Profiles/Tester/bd07.set`
  - InpVersion: `V12XAU1-RESEARCH-BD07`
  - Magic: `212001`
  - 研究参数: `RiskPercent=1.5`, `MaxLotSize=3.0`, `MaxConcurrent=14`, `MaxEntriesPerOB=20`, `OBReentryCooldownMin=0`, `CooldownBars=0`

- XAU2: `temp/mt5_portable_xau_v12/XAU2/MQL5/Presets/v12xau2.set`
  - 来源: `temp/mt5_portable_bt/MQL5/Profiles/Tester/trendhold_24m_tmp.set`
  - InpVersion: `V12XAU2-RESEARCH-RISK8`
  - Magic: `212002`
  - 研究参数: `RiskPercent=8.0`, `MaxLotSize=5.0`, `MaxConcurrent=14`, `MaxEntriesPerOB=20`, `OBReentryCooldownMin=0`, `CooldownBars=0`

## 备份

- 原 live-safe set 已备份到: `results/live/research_param_backups_20260615_163728/`

## 验证

- 旧 live 进程已停止后重启，避免热替换策略版本。
- XAU1 新 PID: 166600
- XAU2 新 PID: 109072
- Terminal Journal:
  - XAU1: `561 inputs read ... v12xau1.set`, `expert WaiTrade_OB (XAUUSDm,M1) loaded successfully`
  - XAU2: `583 inputs read ... v12xau2.set`, `expert WaiTrade_OB (XAUUSDm,M1) loaded successfully`
- EA 日志:
  - XAU1: `WaiTrade2 V12XAU1-RESEARCH-BD07 已加载 | XAUUSDm | Magic=212001`
  - XAU2: `WaiTrade2 V12XAU2-RESEARCH-RISK8 已加载 | XAUUSDm | Magic=212002`
- `InpEnableEntryDebug=true` 已确认保留。
- 重启时终端同步显示 `0 positions, 0 orders`。

## 风险说明

本部署主动解除 `$200` live 安全边界，尤其 XAU2 使用 `risk_percent=8.0`、`max_lot_size=5.0`、`max_concurrent=14`、`max_entries_per_ob=20`。该配置属于研究版参数，实盘风险显著高于 live-safe 版本。
