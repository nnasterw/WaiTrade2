# Portfolio live status

streams=7 pass=false
generated_at=2026-05-26 13:30:16
window_since=2026-05-25 13:30:16
min_uptime_min=1320

## Summary
total_pos=0
ob_streams=6
total_opens=24
total_closes=40
total_errors=0
total_disconnects=54
total_reconnects=54
stale_heartbeats=0
uptime_ok_streams=0/7
min_uptime_min_seen=1252

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 1252 | false | 2026-05-25 16:37:32 | true | true | true | entry_blocked | 51 | true | 0 | 4 | 1540.0 | 63.90 | -1 | 6 | 10 | 0 | 25 | 11 | 5 | 5 | FJ 1 09:58:51.608 Network '277656700': connection to Exness-MT5Trial5 lost | EO 0 09:58:52.546 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 87.79 ms, build ... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=241 / ob=4 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R225 | 27516 | 1252 | false | 2026-05-25 16:37:34 | true | true | true | entry_blocked | 51 | true | 0 | 4 | 1540.0 | 63.90 | -1 | 6 | 10 | 0 | 25 | 11 | 11 | 11 | ER 1 13:22:48.562 Network '277656700': connection to Exness-MT5Trial5 lost | LG 0 13:22:49.747 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 87.39 ms, build ... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=241 / ob=4 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R226 | 21624 | 1252 | false | 2026-05-25 16:37:36 | true | true | true | entry_blocked | 51 | true | 0 | 4 | 1540.0 | 63.90 | -1 | 6 | 10 | 0 | 25 | 12 | 12 | 12 | KE 1 13:23:21.739 Network '277656700': connection to Exness-MT5Trial5 lost | MS 0 13:23:23.095 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.29 ms, build ... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=241 / ob=4 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R211M | 7824 | 1252 | false | 2026-05-25 16:37:25 | true | true | true | load | 51 | true | 0 | 0 | 1540.0 | 63.90 | -1 | 0 | 0 | 0 | 25 | 3 | 8 | 8 | FI 1 13:28:16.955 Network '277656700': connection to Exness-MT5Trial5 lost | HL 0 13:28:17.313 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 105.89 ms, build... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=241 / ob=0 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R213D | 27016 | 1252 | false | 2026-05-25 16:37:27 | true | true | true | load | 51 | true | 0 | 3 | 1540.0 | 63.90 | -1 | 0 | 0 | 0 | 25 | 2 | 8 | 8 | CF 1 13:18:47.027 Network '277656700': connection to Exness-MT5Trial5 lost | QS 0 13:18:47.931 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 90.12 ms, build ... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=241 / ob=3 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R216M | 40024 | 1252 | false | 2026-05-25 16:37:29 | true | true | true | load | 51 | true | 0 | 4 | 1540.0 | 63.90 | -1 | 0 | 0 | 0 | 25 | 2 | 3 | 3 | RJ 1 21:59:06.179 Network '277656700': connection to Exness-MT5Trial5 lost | DL 0 21:59:06.965 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.63 ms, build... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=241 / ob=4 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |
| R227 | 37160 | 1252 | false | 2026-05-25 16:37:38 | true | true | true | entry_blocked | 51 | true | 0 | 4 | 1540.0 | 63.90 | -1 | 6 | 10 | 0 | 25 | 11 | 7 | 7 | IJ 1 21:59:00.394 Network '277656700': connection to Exness-MT5Trial5 lost | GS 0 21:59:01.164 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 134.12 ms, build... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=241 / ob=4 / pos=0 / atr=63.90 / spread=1540.0 / state=-1 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
