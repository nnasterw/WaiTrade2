# Portfolio live status

streams=7 pass=false
generated_at=2026-05-25 13:58:40
window_since=2026-05-24 13:58:40
min_uptime_min=1320

| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | heartbeats | guard_events | disconnects | heartbeat |
|---|---:|---:|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R224 | 18620 | 37 | false | 2026-05-25 13:21:37 | true | true | true | init | 36 | true | 0 | 0 | 1540.0 | 88.74 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | V11-R224-R186CTX35-R224 / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=88.74 / spread=1540.0 / state=1 |
| R225 | 31592 | 36 | false | 2026-05-25 13:21:45 | true | true | true | init | 36 | true | 0 | 0 | 1540.0 | 88.74 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | V11-R225-R196CTX35-R225 / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=88.74 / spread=1540.0 / state=1 |
| R226 | 14352 | 42 | false | 2026-05-25 13:16:22 | true | true | true | init | 42 | true | 0 | 0 | 1540.0 | 86.25 | 1 | 0 | 0 | 0 | 1 | 1 | 2 | V11-R226-R212CTX3-R226 / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=86.25 / spread=1540.0 / state=1 |
| R211M | 12412 | 36 | false | 2026-05-25 13:21:54 | true | true | true | init | 36 | true | 0 | 1 | 1540.0 | 88.74 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | V11-R211-HTFH20R220-R211M / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=88.74 / spread=1540.0 / state=1 |
| R213D | 27304 | 36 | false | 2026-05-25 13:22:03 | true | true | true | init | 36 | true | 0 | 1 | 1540.0 | 88.74 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | V11-R213-R104DECHRS-R213D / BTCUSDm PERIOD_M5 / bar=1 / ob=1 / pos=0 / atr=88.74 / spread=1540.0 / state=1 |
| R216M | 34368 | 36 | false | 2026-05-25 13:22:11 | true | true | true | init | 36 | true | 0 | 0 | 1540.0 | 89.16 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | V11-R216-R39MARHRS-R216M / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=89.16 / spread=1540.0 / state=1 |
| R227 | 24672 | 36 | false | 2026-05-25 13:22:19 | true | true | true | init | 36 | true | 0 | 0 | 1540.0 | 89.16 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | V11-R227-R61CTX35-R227 / BTCUSDm PERIOD_M5 / bar=1 / ob=0 / pos=0 / atr=89.16 / spread=1540.0 / state=1 |

## Caveat
This portable multi-terminal deployment shares broker account state, but MT5 Global Variables are terminal-local. Treat shared monthly guard behavior as not equivalent to a single-terminal multi-chart deployment.
