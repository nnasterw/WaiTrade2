# v11a live start status - 2026-05-25

## Status

v11a live observation started at about 2026-05-25 13:22 Asia/Shanghai.

Backtests are paused. This run is for one-day live/forward observation.

## Deployment

MT5 profile auto-restore did not load the generated seven-chart profile, so v11a is running as seven portable MT5 terminals under:

`D:\Code\codexProject\WaiTrade2\temp\mt5_portable_v11a`

Streams:

- R224: `V11-R224-R186CTX35-R224`, magic `204383`
- R225: `V11-R225-R196CTX35-R225`, magic `204384`
- R226: `V11-R226-R212CTX3-R226`, magic `204385`
- R211M: `V11-R211-HTFH20R220-R211M`, magic `204370`
- R213D: `V11-R213-R104DECHRS-R213D`, magic `204372`
- R216M: `V11-R216-R39MARHRS-R216M`, magic `204375`
- R227: `V11-R227-R61CTX35-R227`, magic `204386`

All seven terminals are authorized on account `277656700`, loaded `WaiTrade_OB`, emitted `SHARED_GUARD event=init`, and printed a `HEARTBEAT`.

## Caveat

This temporary seven-terminal deployment does not provide true cross-terminal shared monthly guard state because the EA uses MT5 `GlobalVariableSet/Get`, which is terminal-local. Account-level positions and trades are shared through the broker account, but `shared_monthly_guard_key=v11a_live20260525` is not a single shared state across these portable data folders.

Use this one-day run mainly to observe live signal/execution behavior, fills, errors, spread, order frequency, and per-stream interactions. Treat account-level monthly guard behavior as not fully equivalent to the intended single-terminal multi-chart deployment.

## Follow-up

A one-day heartbeat review is scheduled for 2026-05-26 13:30 Asia/Shanghai.
