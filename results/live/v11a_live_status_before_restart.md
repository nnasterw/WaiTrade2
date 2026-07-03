# Portfolio live status

streams=7 pass=false
generated_at=2026-05-25 16:36:41
window_since=2026-05-24 16:36:41

## Summary
total_pos=0
ob_streams=7
total_opens=0
total_closes=0
total_errors=0
total_disconnects=26
total_reconnects=19
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=-

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | - | - | true | - | true | true | true | init | 14 | true | 0 | 1 | 1400.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 1 | 3 | 2 | QO 0 16:35:51.890 Network '277656700': disconnected from Exness-MT5Trial5 | HH 0 16:12:28.730 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.11 ms, build ... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=37 / ob=1 / pos=0 / atr=82.71 / spread=1400.0 / state=0 |
| R225 | - | - | true | - | true | true | true | init | 14 | true | 0 | 1 | 1400.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 1 | 3 | 2 | DJ 0 16:35:44.592 Network '277656700': disconnected from Exness-MT5Trial5 | CF 0 15:58:52.313 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 85.36 ms, build ... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=37 / ob=1 / pos=0 / atr=82.71 / spread=1400.0 / state=0 |
| R226 | - | - | true | - | true | true | true | load | 38 | true | 0 | 1 | 1400.0 | 88.90 | 1 | 0 | 0 | 0 | 4 | 2 | 6 | 5 | RJ 0 16:35:34.502 Network '277656700': disconnected from Exness-MT5Trial5 | NK 0 15:58:53.433 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.43 ms, build ... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=88.90 / spread=1400.0 / state=1 |
| R211M | - | - | true | - | true | true | true | load | 14 | true | 0 | 2 | 1540.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 2 | 3 | 2 | GH 0 16:35:39.616 Network '277656700': disconnected from Exness-MT5Trial5 | CO 0 16:35:36.419 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.57 ms, build ... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=37 / ob=2 / pos=0 / atr=82.71 / spread=1540.0 / state=0 |
| R213D | - | - | true | - | true | true | true | init | 14 | true | 0 | 1 | 1540.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 1 | 4 | 3 | LE 0 16:35:50.425 Network '277656700': disconnected from Exness-MT5Trial5 | FR 0 16:21:04.629 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.15 ms, build ... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=37 / ob=1 / pos=0 / atr=82.71 / spread=1540.0 / state=0 |
| R216M | - | - | true | - | true | true | true | init | 14 | true | 0 | 1 | 1400.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 1 | 2 | 1 | KG 0 16:35:42.630 Network '277656700': disconnected from Exness-MT5Trial5 | HJ 0 15:58:52.507 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.65 ms, build ... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=37 / ob=1 / pos=0 / atr=82.71 / spread=1400.0 / state=0 |
| R227 | - | - | true | - | true | true | true | init | 14 | true | 0 | 1 | 1400.0 | 82.71 | 0 | 0 | 0 | 0 | 4 | 1 | 5 | 4 | RP 0 16:35:41.184 Network '277656700': disconnected from Exness-MT5Trial5 | GF 0 16:19:00.525 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #5 (ping: 84.00 ms, build ... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=37 / ob=1 / pos=0 / atr=82.71 / spread=1400.0 / state=0 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
