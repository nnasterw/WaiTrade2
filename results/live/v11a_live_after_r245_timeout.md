# Portfolio live status

streams=7 pass=true
generated_at=2026-05-26 04:29:46
window_since=2026-05-25 04:29:46

## Summary
total_pos=0
ob_streams=7
total_opens=24
total_closes=40
total_errors=0
total_disconnects=44
total_reconnects=44
stale_heartbeats=0
uptime_ok_streams=7/7
min_uptime_min_seen=712

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | last_error | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| R224 | 38968 | 712 | true | 2026-05-25 16:37:32 | true | true | true | entry | 51 | true | 0 | 1 | 1400.0 | 65.40 | 0 | 6 | 10 | 0 | 16 | 8 | 4 | 4 | LH 1 21:59:03.552 Network '277656700': connection to Exness-MT5Trial5 lost | FM 0 21:59:04.374 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 132.62 ms, build... | - | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=133 / ob=1 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R225 | 27516 | 712 | true | 2026-05-25 16:37:34 | true | true | true | entry | 51 | true | 0 | 1 | 1400.0 | 65.40 | 0 | 6 | 10 | 0 | 16 | 8 | 8 | 8 | KP 1 21:59:05.674 Network '277656700': connection to Exness-MT5Trial5 lost | GE 0 21:59:06.480 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 140.80 ms, build... | - | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=133 / ob=1 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R226 | 21624 | 712 | true | 2026-05-25 16:37:36 | true | true | true | entry | 51 | true | 0 | 1 | 1400.0 | 65.40 | 0 | 6 | 10 | 0 | 16 | 9 | 9 | 9 | RR 1 21:59:05.745 Network '277656700': connection to Exness-MT5Trial5 lost | PK 0 21:59:06.546 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 131.08 ms, build... | - | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=133 / ob=1 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R211M | 7824 | 712 | true | 2026-05-25 16:37:25 | true | true | true | load | 51 | true | 0 | 3 | 1400.0 | 65.40 | 0 | 0 | 0 | 0 | 16 | 3 | 7 | 7 | RL 1 03:58:52.126 Network '277656700': connection to Exness-MT5Trial5 lost | MJ 0 03:58:52.848 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #3 (ping: 86.00 ms, build ... | - | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=133 / ob=3 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R213D | 27016 | 712 | true | 2026-05-25 16:37:27 | true | true | true | load | 51 | true | 0 | 2 | 1400.0 | 65.40 | 0 | 0 | 0 | 0 | 16 | 2 | 6 | 6 | PG 1 21:59:00.979 Network '277656700': connection to Exness-MT5Trial5 lost | DF 0 21:59:01.771 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 132.00 ms, build... | - | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=133 / ob=2 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R216M | 40024 | 712 | true | 2026-05-25 16:37:29 | true | true | true | load | 51 | true | 0 | 1 | 1400.0 | 65.40 | 0 | 0 | 0 | 0 | 16 | 2 | 3 | 3 | RJ 1 21:59:06.179 Network '277656700': connection to Exness-MT5Trial5 lost | DL 0 21:59:06.965 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 137.63 ms, build... | - | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=133 / ob=1 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |
| R227 | 37160 | 712 | true | 2026-05-25 16:37:38 | true | true | true | entry | 51 | true | 0 | 1 | 1400.0 | 65.40 | 0 | 6 | 10 | 0 | 16 | 8 | 7 | 7 | IJ 1 21:59:00.394 Network '277656700': connection to Exness-MT5Trial5 lost | GS 0 21:59:01.164 Network '277656700': authorized on Exness-MT5Trial5 through Access Point #2 (ping: 134.12 ms, build... | - | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=133 / ob=1 / pos=0 / atr=65.40 / spread=1400.0 / state=0 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
