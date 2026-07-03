# Portfolio live status

streams=7 pass=true
generated_at=2026-05-26 10:18:48
window_since=2026-05-25 10:18:48

## Summary
total_pos=0
ob_streams=7
total_opens=24
total_closes=40
total_errors=0
total_disconnects=49
total_reconnects=49
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=1061

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 1061 | true | 2026-05-25 16:37:32 | true | true | true | entry_blocked | 40 | true | 0 | 1 | 1400.0 | 148.37 | -1 | 6 | 10 | 0 | 22 | 10 | 5 | 5 | FJ 1 09:58:51.608 Network '277656700': connection to Exness-MT5Trial5 lost | EO 0 09:58:52.546 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 87.79 ms, build ... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=205 / ob=1 / pos=0 / atr=148.37 / spread=1400.0 / state=-1 |
| R225 | 27516 | 1061 | true | 2026-05-25 16:37:34 | true | true | true | entry_blocked | 40 | true | 0 | 1 | 1400.0 | 148.37 | -1 | 6 | 10 | 0 | 22 | 10 | 10 | 10 | EF 1 10:08:55.475 Network '277656700': connection to Exness-MT5Trial5 lost | GS 0 10:08:56.491 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 87.39 ms, build ... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=205 / ob=1 / pos=0 / atr=148.37 / spread=1400.0 / state=-1 |
| R226 | 21624 | 1061 | true | 2026-05-25 16:37:36 | true | true | true | entry_blocked | 40 | true | 0 | 1 | 1400.0 | 148.37 | -1 | 6 | 10 | 0 | 22 | 11 | 10 | 10 | IJ 1 09:58:53.382 Network '277656700': connection to Exness-MT5Trial5 lost | RO 0 09:58:54.314 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 88.29 ms, build ... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=205 / ob=1 / pos=0 / atr=148.37 / spread=1400.0 / state=-1 |
| R211M | 7824 | 1061 | true | 2026-05-25 16:37:25 | true | true | true | load | 40 | true | 0 | 4 | 1540.0 | 148.37 | -1 | 0 | 0 | 0 | 22 | 3 | 7 | 7 | RL 1 03:58:52.126 Network '277656700': connection to Exness-MT5Trial5 lost | MJ 0 03:58:52.848 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 86.00 ms, build ... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=205 / ob=4 / pos=0 / atr=148.37 / spread=1540.0 / state=-1 |
| R213D | 27016 | 1061 | true | 2026-05-25 16:37:27 | true | true | true | load | 40 | true | 0 | 2 | 1540.0 | 148.37 | -1 | 0 | 0 | 0 | 22 | 2 | 7 | 7 | QJ 1 09:58:52.330 Network '277656700': connection to Exness-MT5Trial5 lost | PO 0 09:58:53.222 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 90.12 ms, build ... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=205 / ob=2 / pos=0 / atr=148.37 / spread=1540.0 / state=-1 |
| R216M | 40024 | 1061 | true | 2026-05-25 16:37:29 | true | true | true | load | 40 | true | 0 | 1 | 1400.0 | 148.37 | -1 | 0 | 0 | 0 | 22 | 2 | 3 | 3 | RJ 1 21:59:06.179 Network '277656700': connection to Exness-MT5Trial5 lost | DL 0 21:59:06.965 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.63 ms, build... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=205 / ob=1 / pos=0 / atr=148.37 / spread=1400.0 / state=-1 |
| R227 | 37160 | 1061 | true | 2026-05-25 16:37:38 | true | true | true | entry_blocked | 39 | true | 0 | 1 | 1540.0 | 148.37 | -1 | 6 | 10 | 0 | 22 | 10 | 7 | 7 | IJ 1 21:59:00.394 Network '277656700': connection to Exness-MT5Trial5 lost | GS 0 21:59:01.164 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 134.12 ms, build... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=205 / ob=1 / pos=0 / atr=148.37 / spread=1540.0 / state=-1 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
