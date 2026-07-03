# Portfolio live status

streams=7 pass=false
generated_at=2026-05-27 18:18:58

## Summary
total_pos=0
ob_streams=7
total_opens=0
total_closes=0
total_errors=0
total_disconnects=131
total_reconnects=124
stale_heartbeats=7
uptime_ok_streams=7/7
min_uptime_min_seen=-

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | - | - | true | - | true | true | false | entry_blocked | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 12 | 14 | 13 | MS 0 11:48:15.248 Network '277656700': disconnected from Exness-MT5Trial5 | MP 0 09:59:04.048 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.73 ms, build... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R225 | - | - | true | - | true | true | false | entry_blocked | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 12 | 28 | 27 | CE 0 11:48:15.273 Network '277656700': disconnected from Exness-MT5Trial5 | LR 0 11:47:49.447 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 103.25 ms, build... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R226 | - | - | true | - | true | true | true | entry_blocked | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 12 | 17 | 16 | GG 0 11:48:14.995 Network '277656700': disconnected from Exness-MT5Trial5 | OS 0 09:59:03.235 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.32 ms, build... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R211M | - | - | true | - | true | true | true | - | 399 | false | 0 | 4 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 0 | 17 | 16 | KG 0 11:48:14.953 Network '277656700': disconnected from Exness-MT5Trial5 | CL 0 09:59:01.703 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 132.53 ms, build... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=517 / ob=4 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R213D | - | - | true | - | true | true | false | - | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 0 | 21 | 20 | LG 0 11:48:15.278 Network '277656700': disconnected from Exness-MT5Trial5 | QL 0 10:16:33.458 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 140.64 ms, build... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R216M | - | - | true | - | true | true | false | - | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 0 | 16 | 15 | OM 0 11:48:14.928 Network '277656700': disconnected from Exness-MT5Trial5 | HN 0 00:50:38.749 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 167.51 ms, build... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |
| R227 | - | - | true | - | true | true | false | entry_blocked | 399 | false | 0 | 2 | 1540.0 | 74.85 | -1 | 0 | 0 | 0 | 36 | 12 | 18 | 17 | OJ 0 11:48:15.284 Network '277656700': disconnected from Exness-MT5Trial5 | EF 0 23:56:00.625 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 130.07 ms, build... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=517 / ob=2 / pos=0 / atr=74.85 / spread=1540.0 / state=-1 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
