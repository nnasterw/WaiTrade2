# Portfolio live status

streams=7 pass=false
generated_at=2026-05-27 11:38:51
window_since=2026-05-27 05:38:51

## Summary
total_pos=0
ob_streams=7
total_opens=0
total_closes=0
total_errors=0
total_disconnects=12
total_reconnects=12
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=2581

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 2581 | true | 2026-05-25 16:37:32 | true | true | false | entry_blocked | 59 | true | 0 | 2 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 4 | 2 | 2 | LF 1 09:59:02.993 Network '277656700': connection to Exness-MT5Trial5 lost | MP 0 09:59:04.048 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.73 ms, build... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R225 | 27516 | 2581 | true | 2026-05-25 16:37:34 | true | true | false | entry_blocked | 59 | true | 0 | 2 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 4 | 4 | 4 | NH 1 10:50:03.034 Network '277656700': connection to Exness-MT5Trial5 lost | IN 0 10:50:03.849 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 103.25 ms, build... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R226 | 21624 | 2581 | true | 2026-05-25 16:37:36 | true | true | true | entry_blocked | 59 | true | 0 | 2 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 4 | 3 | 3 | DJ 1 09:59:02.304 Network '277656700': connection to Exness-MT5Trial5 lost | OS 0 09:59:03.235 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.32 ms, build... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R211M | 7824 | 2581 | true | 2026-05-25 16:37:25 | true | true | true | - | 59 | true | 0 | 2 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 0 | 1 | 1 | IJ 1 09:59:00.842 Network '277656700': connection to Exness-MT5Trial5 lost | CL 0 09:59:01.703 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 132.53 ms, build... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R213D | 27016 | 2581 | true | 2026-05-25 16:37:27 | true | true | false | - | 59 | true | 0 | 3 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 0 | 2 | 2 | KJ 1 10:16:32.570 Network '277656700': connection to Exness-MT5Trial5 lost | QL 0 10:16:33.458 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 140.64 ms, build... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=505 / ob=3 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R216M | 40024 | 2581 | true | 2026-05-25 16:37:29 | true | true | false | - | 59 | true | 0 | 2 | 1540.0 | 90.40 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | - | - | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.40 / spread=1540.0 / state=0 |
| R227 | 37160 | 2581 | true | 2026-05-25 16:37:38 | true | true | false | entry_blocked | 59 | true | 0 | 2 | 1540.0 | 90.68 | 0 | 0 | 0 | 0 | 12 | 4 | 0 | 0 | - | - | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=505 / ob=2 / pos=0 / atr=90.68 / spread=1540.0 / state=0 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
