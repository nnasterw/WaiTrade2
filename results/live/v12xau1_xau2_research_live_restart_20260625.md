# v12 XAU1 + XAU2 研究版 Live 启动记录 - 2026-06-25

## 操作

- XAU1: 启动 `temp/mt5_portable_xau_v12/XAU1/terminal64.exe /portable /config:v12xau1_live_startup.ini`
- XAU2: 旧进程存在但当日 EA 日志未刷新，先停止后重启 `temp/mt5_portable_xau_v12/XAU2/terminal64.exe /portable /config:v12xau2_live_startup.ini`
- 账号: Exness-MT5Trial5 / `277656700`
- 品种/周期: `XAUUSDm` / `M1`

## 当前进程

- XAU1 PID: `8108`
- XAU2 PID: `11384`

## 参数确认

### XAU1

- Preset: `temp/mt5_portable_xau_v12/XAU1/MQL5/Presets/v12xau1.set`
- `InpVersion=V12XAU1-RESEARCH-BD07`
- `InpMagicNumber=212001`
- `InpRiskPercent=1.5`
- `InpMaxLotSize=3.0`
- `InpMaxConcurrent=14`
- `InpMaxEntriesPerOB=20`
- `InpOBReentryCooldownMin=0`
- `InpCooldownBars=0`
- `InpEnableEntryDebug=true`

### XAU2

- Preset: `temp/mt5_portable_xau_v12/XAU2/MQL5/Presets/v12xau2.set`
- `InpVersion=V12XAU2-RESEARCH-RISK8`
- `InpMagicNumber=212002`
- `InpRiskPercent=8.0`
- `InpMaxLotSize=5.0`
- `InpMaxConcurrent=14`
- `InpMaxEntriesPerOB=20`
- `InpOBReentryCooldownMin=0`
- `InpCooldownBars=0`
- `InpEnableEntryDebug=true`

## 验证

- XAU1 terminal: `561 inputs read ... v12xau1.set`
- XAU1 terminal: `expert WaiTrade_OB (XAUUSDm,M1) loaded successfully`
- XAU1 terminal: `terminal synchronized ... 0 positions, 0 orders`
- XAU1 terminal: `trading has been enabled - hedging mode`
- XAU2 terminal: `583 inputs read ... v12xau2.set`
- XAU2 terminal: `expert WaiTrade_OB (XAUUSDm,M1) loaded successfully`
- XAU2 terminal: `terminal synchronized ... 0 positions, 0 orders`
- XAU2 terminal: `trading has been enabled - hedging mode`

## 备注

- 本次按用户要求使用研究版参数，未套用 `$200` live-safe 限制。
- XAU2 重启前在 `19:16` 附近已有两笔成交记录: buy `0.03` 与 sell `0.03`。
