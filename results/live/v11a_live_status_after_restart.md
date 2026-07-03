# Portfolio live status

streams=7 pass=true
generated_at=2026-05-25 16:42:12
window_since=2026-05-24 16:42:12

## Summary
total_pos=0
ob_streams=6
total_opens=0
total_closes=0
total_errors=0
total_disconnects=26
total_reconnects=26
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=4

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 4 | true | 2026-05-25 16:37:32 | true | true | true | load | 4 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 2 | 3 | 3 | QO 0 16:35:51.890 Network '277656700': disconnected from Exness-MT5Trial5 | JI 0 16:37:58.675 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.11 ms, build ... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R225 | 27516 | 4 | true | 2026-05-25 16:37:34 | true | true | true | load | 4 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 2 | 3 | 3 | DJ 0 16:35:44.592 Network '277656700': disconnected from Exness-MT5Trial5 | JN 0 16:38:01.874 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 85.36 ms, build ... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R226 | 21624 | 4 | true | 2026-05-25 16:37:36 | true | true | true | load | 4 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 3 | 6 | 6 | RJ 0 16:35:34.502 Network '277656700': disconnected from Exness-MT5Trial5 | JF 0 16:38:04.302 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.43 ms, build ... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R211M | 7824 | 4 | true | 2026-05-25 16:37:25 | true | true | true | load | 4 | true | 0 | 0 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 3 | 3 | 3 | GH 0 16:35:39.616 Network '277656700': disconnected from Exness-MT5Trial5 | FR 0 16:37:29.735 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.57 ms, build ... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R213D | 27016 | 4 | true | 2026-05-25 16:37:27 | true | true | true | load | 4 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 2 | 4 | 4 | LE 0 16:35:50.425 Network '277656700': disconnected from Exness-MT5Trial5 | NS 0 16:37:34.696 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.15 ms, build ... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R216M | 40024 | 4 | true | 2026-05-25 16:37:29 | true | true | true | load | 4 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 2 | 2 | 2 | KG 0 16:35:42.630 Network '277656700': disconnected from Exness-MT5Trial5 | CQ 0 16:37:53.101 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 89.65 ms, build ... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |
| R227 | 37160 | 4 | true | 2026-05-25 16:37:38 | true | true | true | load | 3 | true | 0 | 1 | 1540.0 | 71.08 | 0 | 0 | 0 | 0 | 5 | 2 | 5 | 5 | RP 0 16:35:41.184 Network '277656700': disconnected from Exness-MT5Trial5 | EH 0 16:38:11.250 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #5 (ping: 84.00 ms, build ... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=71.08 / spread=1540.0 / state=0 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
