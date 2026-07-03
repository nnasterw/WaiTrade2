# v12 XAU2 Live 重启记录 - 2026-06-22

## 操作

- 启动: `temp/mt5_portable_xau_v12/XAU2/terminal64.exe /portable /config:v12xau2_live_startup.ini`
- PID: `3636`
- 账号: Exness-MT5Trial5 / `277656700`
- 品种/周期: `XAUUSDm` / `M1`

## 参数确认

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

## 日志验证

- Terminal 日志: `583 inputs read ... v12xau2.set`
- Terminal 日志: `expert WaiTrade_OB (XAUUSDm,M1) loaded successfully`
- Terminal 日志: `trading has been enabled - hedging mode`
- EA 日志: `WaiTrade2 V12XAU2-RESEARCH-RISK8 已加载 | XAUUSDm | Magic=212002`
- EA 日志: `HEARTBEAT V12XAU2-RESEARCH-RISK8 | XAUUSDm PERIOD_M1`

## 风险说明

本次运行的是研究版 XAU2 参数，未套用 `$200` live-safe 限制。
