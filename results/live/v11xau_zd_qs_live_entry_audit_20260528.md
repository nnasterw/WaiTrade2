# V11XAU ZD/QS Live Entry Audit - 2026-05-28

## Scope

- Account: `277656700` on `Exness-MT5Trial5`
- Symbol: `XAUUSDm`
- Live instances:
  - `V11XAU-ZD`, magic `204800`, `PERIOD_M3`, PID observed: `36116`
  - `V11XAU-QS`, magic `204801`, `PERIOD_M1`, PID observed: `35568`
- Source logs:
  - `temp/mt5_portable_xau_zd_qs/ZD/MQL5/Logs/20260528.log`
  - `temp/mt5_portable_xau_zd_qs/QS/MQL5/Logs/20260528.log`
  - `temp/mt5_portable_xau_zd_qs/QS/Logs/20260528.log`
- Review window: mainly `22:00` to `22:53` Asia/Shanghai.

## Live State Observed

`V11XAU-ZD` did not produce entries in the reviewed window. Heartbeats show it had no active OB by the relevant period:

```text
21:36:23 HEARTBEAT V11XAU-ZD | XAUUSDm PERIOD_M3 | bar=61 | ob=0 | pos=0 | atr=6.771 | spread=308.0 | state=0
22:36:23 HEARTBEAT V11XAU-ZD | XAUUSDm PERIOD_M3 | bar=81 | ob=0 | pos=0 | atr=10.253 | spread=308.0 | state=0
```

`V11XAU-QS` had active OBs and was responsible for the entries:

```text
21:36:23 HEARTBEAT V11XAU-QS | XAUUSDm PERIOD_M1 | bar=181 | ob=1 | pos=0 | atr=3.608 | spread=308.0 | state=1
22:36:23 HEARTBEAT V11XAU-QS | XAUUSDm PERIOD_M1 | bar=241 | ob=2 | pos=0 | atr=4.269 | spread=308.0 | state=1
```

## QS Entries And Outcomes

```text
22:03:16 buy 0.01 @ 4423.062, SL 4420.711, TP 4427.129
22:04:29 SL modified to 4424.089
22:04:30 sell 0.01 @ 4424.089
Outcome: BE/locked profit exit

22:47:23 buy 0.04 @ 4469.233, SL 4467.213, TP 4472.263
22:47:29 sell 0.04 @ 4467.213
Outcome: stop loss

22:48:01 buy 0.07 @ 4468.820, SL 4467.142, TP 4470.810
22:48:04 SL modified to 4469.407
22:48:05 sell 0.07 @ 4469.407
Outcome: BE/locked profit exit

22:49:18 buy 0.04 @ 4469.246, SL 4467.063, TP 4472.711
22:49:24 sell 0.04 @ 4467.063
Outcome: stop loss

22:50:03 buy 0.09 @ 4468.471, SL 4467.025, TP 4469.493
22:50:08 SL modified to 4468.866
22:50:08 sell 0.09 @ 4468.707
Outcome: exit after BE/lock adjustment, filled below modified SL

22:51:02 buy 0.01 @ 4470.226, SL 4467.037, TP 4474.591
22:51:54 SL modified to 4471.435
22:51:58 sell 0.01 @ 4471.435
Outcome: BE/locked profit exit

22:52:03 buy 0.01 @ 4469.652, SL 4467.072, TP 4473.523
22:52:37 sell 0.01 @ 4467.072
Outcome: stop loss

22:53:01 buy 0.01 @ 4470.034, SL 4467.076, TP 4473.441
22:53:27 SL modified to 4471.052
22:53:34 sell 0.01 @ 4470.980
Outcome: exit after BE/lock adjustment, filled below modified SL
```

EA-side entry diagnostics were disabled in the deployed set (`InpEnableEntryDebug=false`), so the live log records successful entries but not skipped candidates or exact filter rejection reasons.

## Relevant QS Live Parameters

From `temp/mt5_portable_xau_zd_qs/QS/MQL5/Presets/v11xau_live_QS.set`:

```text
InpBarTF=1
InpEnableXAUTrendProfile=false
InpMaxConcurrent=14
InpCooldownBars=0
InpMaxEntriesPerOB=20
InpOBReentryCooldownMin=0
InpMinOBStrength=0.5
InpMinScore=0
InpEntryDepthFilter=true
InpEntryDepthPct=0.67
InpBouncePct=0.18
InpMaxEntryOffsetR=1.2
InpMinRiskSpreadRatio=2.5
InpEnableEntryDebug=false
```

## Preliminary Diagnosis

1. The missed "good-looking" opportunities cannot be fully explained from current live logs because skip diagnostics were disabled. Candidates may have failed to become EA-recognized M1 OBs, failed depth touch, bounce, offset, market-state alignment, spread/risk, or other filters.

2. The entries after `22:47` are consistent with QS being configured for very permissive re-entry:
   - `InpMaxEntriesPerOB=20`
   - `InpOBReentryCooldownMin=0`
   - `InpCooldownBars=0`
   - `InpMaxConcurrent=14`

   This allows rapid repeated entries in the same or nearby OB context immediately after a stop.

3. ZD was not the source of the problematic entries in this window; ZD had `ob=0` at the hourly heartbeats around the event.

4. A same-day half-hour Strategy Tester replay was attempted, but MT5 tester did not provide a reliable current-day partial replay. The tester config is date-granularity based; `2026.05.28 ~ 2026.05.29` returned `tester didn't start`, while completed 720-day tests ending at `2026.05.28` only covered through `2026.05.27 23:59:58`.

## Suggested Next Actions

- Preserve live as-is until a parameter change is validated.
- Enable targeted entry diagnostics for QS in a controlled live restart or a separate diagnostic instance:
  - `InpEnableEntryDebug=true`
- Evaluate a QS re-entry guard variant before deployment:
  - `max_entries_per_ob: 3`
  - `ob_reentry_cooldown_min: 30`
  - `cooldown_bars: 1`
- If skipping "good signals" remains a concern, capture debug lines with `MON_DIAG`, `FINAL_DIAG`, and `ENTRY_DIAG` around the next similar window.
