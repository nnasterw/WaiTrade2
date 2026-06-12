# Portfolio Scheduler Runbook

This runbook is for the BTC portfolio schedules.

Current best proxy schedule:
- `config/portfolio_schedules.yaml`
- schedule: `r186_r196_r212_r211_r213_r216_guard`
- symbol: `BTCUSDm`

Previous baseline schedules:
- `config/portfolio_schedules.yaml`
- schedule: `r186_r196_season_guard`
- schedule: `r186_r196_r117_season_guard`
- schedule: `r186_r196_r117_robust_guard`
- schedule: `r186_r196_r117_r209_march_guard`
- schedule: `r186_r196_r117_r211_march_guard`
- schedule: `r186_r196_r212_r211_march_guard`
- schedule: `r186_r196_r212_r211_r213_dec_guard`
- symbol: `BTCUSDm`

Generate a fresh dry-run profile:

```powershell
python scripts\portfolio_schedule_lint.py --schedule r186_r196_r212_r211_r213_r216_guard
python scripts\mt5_portfolio_live_profile.py --schedule r186_r196_r212_r211_r213_r216_guard --guard-key-suffix dryrun_YYYYMMDD
python scripts\mt5_portfolio_profile_audit.py --profile-dir temp\portfolio_profiles\r186_r196_r212_r211_r213_r216_guard --schedule r186_r196_r212_r211_r213_r216_guard
```

Run the full Windows preflight gate without starting MT5:

```powershell
python scripts\portfolio_preflight_win.py --schedule r186_r196_r212_r211_r213_r216_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun --guard-key-suffix dryrun_YYYYMMDD --output results\backtest\portfolio_r186_r196_r212_r211_r213_r216_guard_preflight_YYYYMMDD.md --compile
```

The preflight gate runs:
- schedule/live lint
- path-level proxy target audit
- fixed-cost stress, requiring the schedule's `preflight.require_cost_pass` cost to keep zero bad months
- shared-return proxy target audit
- Windows MetaEditor compile log validation
- profile deploy without starting MT5
- generated and installed profile audits

Generated profile:

```text
temp\portfolio_profiles\r186_r196_r212_r211_r213_r216_guard
```

Deploy the profile into Windows MT5 without starting the terminal:

```powershell
python scripts\portfolio_schedule_lint.py --schedule r186_r196_r212_r211_r213_r216_guard
python scripts\mt5_portfolio_deploy_win.py --schedule r186_r196_r212_r211_r213_r216_guard --profile-name WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun --guard-key-suffix dryrun_YYYYMMDD --compile
python scripts\mt5_portfolio_profile_audit.py --profile-dir "$env:APPDATA\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun" --schedule r186_r196_r212_r211_r213_r216_guard
```

The command installs:

```text
%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Charts\WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun
```

It also syncs:
- `mql5\Experts`
- `mql5\Include`
- `mql5\Scripts`

Windows compile check:

```powershell
python scripts\mt5_compile_win.py
```

The Windows MetaEditor can return a non-zero process code even when compile succeeds. Trust this script's log parser: success requires `Result: 0 errors` in the MetaEditor log.

Start manually only after checking the manifest:

```powershell
& "C:\Program Files\MetaTrader 5\terminal64.exe" /profile:WaiTrade2_Portfolio_BTC_R212_R211_R213_R216_DryRun
```

Expected chart layout:
- `chart01.chr`: R186, magic `204345`
- `chart02.chr`: R196, magic `204355`
- `chart03.chr`: R212, magic `204371`, `InpHighBalanceNoEntryMonths=5`, `InpHighBalanceNoEntryMinMonthStartBalance=5000`
- `chart04.chr`: R211M, magic `204370`, `InpEntryMonths=3`, `InpHTFPullbackRiskMin=220`, `InpHTFPullbackRiskMax=300`
- `chart05.chr`: R213D, magic `204372`, `InpEntryMonths=12`, `InpNoEntryHours=0,1,2,3,4,5,7,8,9,10,12,13,16,17,19,20,21,22,23`
- `chart06.chr`: R216M, magic `204375`, `InpEntryMonths=3`, `InpNoEntryHours=0,1,3,4,5,6,7,8,9,10,12,14,15,17,18,19,20,21,22`
- all charts must use the same `InpSharedMonthlyGuardKey`

Before reusing an old shared guard key, clear MT5 Terminal Global Variables:

1. Open MT5 Navigator -> Scripts -> `WaiTrade2\ClearSharedMonthlyGuard`.
2. Set `InpSharedMonthlyGuardKey` to the exact key shown in `portfolio_manifest.yaml`.
3. Run the script.

Safer option:
- Prefer generating a new profile with a fresh `--guard-key-suffix` for every demo/forward dry-run.

Audit shared guard diagnostics after a dry-run:

```powershell
python scripts\shared_guard_log_audit.py --log path\to\mt5.log --expect-key r186_r196_r212_r211_r213_r216_guard_dryrun_YYYYMMDD --expect-version V11-R186-OB8TAIL-R186 --expect-version V11-R196-STOB4PT1M300-R196 --expect-version V11-R212-R117NOMAYHI-R212 --expect-version V11-R211-HTFH20R220-R211M --expect-version V11-R213-R104DECHRS --expect-version V11-R216-R39MARHRS
```

Run proxy audits:

```powershell
python scripts\portfolio_schedule_runner.py --schedule r186_r196_r212_r211_r213_r216_guard
python scripts\portfolio_return_sim.py --schedule r186_r196_r212_r211_r213_r216_guard
python scripts\portfolio_schedule_stress.py --schedule r186_r196_r212_r211_r213_r216_guard
```

Current best preflight gate:
- `r186_r196_r212_r211_r213_r216_guard` sets `preflight.require_cost_pass: 1.0`.
- A default preflight run for this schedule must keep zero bad months at `1.00/entry`.
- The current schedule also extends the high-balance sweep context to months `3,5`; May uses the same `0,1,6,23` no-entry hours only when month-start balance is high and day <= 2.

Current limitation:
- This profile is for forward/live validation. It is not yet a valid 720-day MT5 Strategy Tester portfolio backtest.
