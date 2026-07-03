# Portfolio live status

streams=7 pass=true
generated_at=2026-05-27 00:00:01
window_since=2026-05-26 00:00:01

## Summary
total_pos=0
ob_streams=7
total_opens=24
total_closes=40
total_errors=0
total_disconnects=150
total_reconnects=150
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=1882

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 1882 | true | 2026-05-25 16:37:32 | true | true | true | entry_blocked | 21 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 6 | 10 | 0 | 36 | 17 | 15 | 15 | DN 1 23:58:43.061 Network '277656700': connection to Exness-MT5Trial5 lost | NK 0 23:58:43.995 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 90.29 ms, build ... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R225 | 27516 | 1882 | true | 2026-05-25 16:37:34 | true | true | true | entry_blocked | 21 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 6 | 10 | 0 | 36 | 17 | 30 | 30 | HH 1 23:26:56.927 Network '277656700': connection to Exness-MT5Trial5 lost | PM 0 23:26:57.800 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 91.87 ms, build ... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R226 | 21624 | 1882 | true | 2026-05-25 16:37:36 | true | true | true | entry_blocked | 21 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 6 | 10 | 0 | 36 | 18 | 20 | 20 | HQ 1 23:32:18.346 Network '277656700': connection to Exness-MT5Trial5 lost | CF 0 23:32:21.017 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 74.89 ms, build ... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R211M | 7824 | 1882 | true | 2026-05-25 16:37:25 | true | true | true | load | 21 | true | 0 | 4 | 1540.0 | 281.96 | 0 | 0 | 0 | 0 | 36 | 3 | 21 | 21 | JQ 1 23:02:14.466 Network '277656700': connection to Exness-MT5Trial5 lost | LG 0 23:02:22.783 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 92.57 ms, build ... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=373 / ob=4 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R213D | 27016 | 1882 | true | 2026-05-25 16:37:27 | true | true | true | load | 21 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 0 | 0 | 0 | 36 | 2 | 25 | 25 | PL 1 23:59:09.556 Network '277656700': connection to Exness-MT5Trial5 lost | KJ 0 23:59:14.515 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 147.60 ms, build... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R216M | 40024 | 1882 | true | 2026-05-25 16:37:29 | true | true | true | load | 21 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 0 | 0 | 0 | 36 | 2 | 15 | 15 | MR 1 23:33:35.567 Network '277656700': connection to Exness-MT5Trial5 lost | OD 0 23:33:36.186 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 167.51 ms, build... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |
| R227 | 37160 | 1882 | true | 2026-05-25 16:37:38 | true | true | true | entry_blocked | 20 | true | 0 | 1 | 1540.0 | 281.96 | 0 | 6 | 10 | 0 | 36 | 17 | 24 | 24 | FP 1 23:55:59.265 Network '277656700': connection to Exness-MT5Trial5 lost | EF 0 23:56:00.625 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 130.07 ms, build... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=373 / ob=1 / pos=0 / atr=281.96 / spread=1540.0 / state=0 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
