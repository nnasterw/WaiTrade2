from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.portfolio_live_status import (
    ERROR_RE,
    StreamStatus,
    combined_log_text,
    filter_since,
    guard_event,
    heartbeat_fields,
    heartbeat_info,
    heartbeat_text,
    newest_log,
    recent_logs,
    reconnect_info,
    render,
    table_cell,
    to_int,
)


def test_extracts_latest_guard_event_and_heartbeat():
    text = "\n".join(
        [
            "x SHARED_GUARD event=init key=demo version=R1 symbol=BTCUSDm month=202605 start=200 peak=200 count=0",
            "x 13:33:00.000 HEARTBEAT R1 | BTCUSDm PERIOD_M5 | bar=1 | ob=0 | pos=0",
            "x SHARED_GUARD event=entry key=demo version=R1 symbol=BTCUSDm month=202605 start=200 peak=210 count=1",
            "x 13:34:00.000 HEARTBEAT R1 | BTCUSDm PERIOD_M5 | bar=2 | ob=1 | pos=1",
        ]
    )

    assert guard_event(text) == "entry"
    assert heartbeat_text(text) == "R1 | BTCUSDm PERIOD_M5 | bar=2 | ob=1 | pos=1"
    assert heartbeat_info(text, None, datetime(2026, 5, 25, 13, 40))[1] == 6
    assert heartbeat_fields(heartbeat_text(text)) == {"bar": "2", "ob": "1", "pos": "1"}


def test_render_fails_when_required_status_missing():
    report = render(
        [
            StreamStatus(
                stream="R1",
                version="R1",
                magic="1",
                path=Path("unused"),
                process_id="",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R1",
                heartbeat_age_min=1,
                heartbeat_fresh=True,
                opens=0,
                closes=0,
                errors=0,
                heartbeats=1,
                guard_events=1,
                disconnects=0,
            )
        ],
        caveat=True,
    )

    assert "streams=1 pass=false" in report
    assert "Global Variables are terminal-local" in report


def test_render_includes_report_times_when_provided():
    report = render(
        [],
        caveat=False,
        generated_at=datetime(2026, 5, 25, 14, 0),
        since=datetime(2026, 5, 24, 14, 0),
    )

    assert "generated_at=2026-05-25 14:00:00" in report
    assert "window_since=2026-05-24 14:00:00" in report


def test_render_includes_portfolio_summary():
    report = render(
        [
            StreamStatus(
                stream="R1",
                version="R1",
                magic="1",
                path=Path("unused"),
                process_id="123",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R1",
                heartbeat_age_min=1,
                heartbeat_fresh=True,
                opens=2,
                closes=1,
                errors=0,
                heartbeats=3,
                guard_events=1,
                disconnects=1,
                reconnects=1,
                latest_pos="1",
                latest_ob="1",
                uptime_min=130,
            ),
            StreamStatus(
                stream="R2",
                version="R2",
                magic="2",
                path=Path("unused"),
                process_id="456",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R2",
                heartbeat_age_min=99,
                heartbeat_fresh=False,
                opens=1,
                closes=0,
                errors=1,
                heartbeats=1,
                guard_events=1,
                disconnects=0,
                reconnects=0,
                latest_pos="0",
                latest_ob="0",
                uptime_min=60,
            ),
        ],
        caveat=False,
        min_uptime_min=120,
    )

    assert "## Summary" in report
    assert "total_pos=1" in report
    assert "ob_streams=1" in report
    assert "total_opens=3" in report
    assert "total_closes=1" in report
    assert "total_errors=1" in report
    assert "total_disconnects=1" in report
    assert "total_reconnects=1" in report
    assert "stale_heartbeats=1" in report
    assert "uptime_ok_streams=1/2" in report
    assert "min_uptime_min_seen=60" in report


def test_render_fails_when_heartbeat_is_stale():
    report = render(
        [
            StreamStatus(
                stream="R1",
                version="R1",
                magic="1",
                path=Path("unused"),
                process_id="123",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R1",
                heartbeat_age_min=90,
                heartbeat_fresh=False,
                opens=0,
                closes=0,
                errors=0,
                heartbeats=1,
                guard_events=1,
                disconnects=0,
            )
        ],
        caveat=False,
    )

    assert "streams=1 pass=false" in report
    assert "| R1 | 123 | - | true | - | true | true | true | init | 90 | false |" in report
    assert (
        "| stream | pid | uptime_min | uptime_ok | started | authorized | trading | loaded | guard | "
        "hb_age_min | hb_fresh | pos | ob | spread | atr | state | opens | closes | errors | "
        "heartbeats | guard_events | disconnects | reconnects | last_disconnect | last_reconnect | "
        "last_error | heartbeat |"
    ) in report


def test_render_can_require_minimum_uptime():
    report = render(
        [
            StreamStatus(
                stream="R1",
                version="R1",
                magic="1",
                path=Path("unused"),
                process_id="123",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R1",
                heartbeat_age_min=1,
                heartbeat_fresh=True,
                opens=0,
                closes=0,
                errors=0,
                heartbeats=1,
                guard_events=1,
                disconnects=0,
                uptime_min=60,
            )
        ],
        caveat=False,
        min_uptime_min=120,
    )

    assert "streams=1 pass=false" in report
    assert "min_uptime_min=120" in report
    assert "| R1 | 123 | 60 | false |" in report


def test_filter_since_keeps_recent_timestamped_and_untimestamped_lines():
    text = "\n".join(
        [
            "13:00:00.000 old line",
            "13:45:00.000 recent line",
            "untimestamped diagnostic",
        ]
    )

    filtered = filter_since(text, None, datetime(2026, 5, 25, 14, 0), datetime(2026, 5, 25, 13, 30))

    assert "old line" not in filtered
    assert "recent line" in filtered
    assert "untimestamped diagnostic" in filtered


def test_error_regex_ignores_liveupdate_download_failure():
    assert not ERROR_RE.search("13:37:55.577 LiveUpdate download 'MT5CLWIDE64' failed")
    assert ERROR_RE.search("13:37:55.577 Experts retcode=10016")


def test_render_includes_last_disconnect_and_error_summaries():
    report = render(
        [
            StreamStatus(
                stream="R1",
                version="R1",
                magic="1",
                path=Path("unused"),
                process_id="123",
                authorized=True,
                trading_enabled=True,
                loaded=True,
                guard_event="init",
                heartbeat="R1 | BTCUSDm",
                heartbeat_age_min=1,
                heartbeat_fresh=True,
                opens=0,
                closes=0,
                errors=1,
                heartbeats=1,
                guard_events=1,
                disconnects=1,
                last_disconnect="13:00:00.000 network disconnected",
                reconnects=1,
                last_reconnect="13:00:01.000 authorized on server through Access Point #1",
                last_error="13:01:00.000 retcode=10016 | invalid stops",
            )
        ],
        caveat=False,
    )

    assert "13:00:00.000 network disconnected" in report
    assert "13:00:01.000 authorized on server through Access Point #1" in report
    assert "13:01:00.000 retcode=10016 / invalid stops" in report


def test_table_cell_compacts_and_escapes_markdown_table_pipes():
    assert table_cell("a | b") == "a / b"
    assert table_cell("abcdef", max_len=5) == "ab..."


def test_to_int_returns_zero_for_non_numeric_values():
    assert to_int("3") == 3
    assert to_int("-") == 0


def test_reconnect_info_counts_authorization_after_disconnect():
    text = "\n".join(
        [
            "13:00:00.000 authorized on server through Access Point #1",
            "13:01:00.000 connection to server lost",
            "13:01:01.000 authorized on server through Access Point #1",
            "13:02:00.000 connection to server lost",
            "13:02:03.000 authorized on server through Access Point #1",
        ]
    )

    count, last = reconnect_info(text)

    assert count == 2
    assert last == "13:02:03.000 authorized on server through Access Point #1"


def test_newest_log_ignores_metaeditor_log(tmp_path):
    terminal_log = tmp_path / "20260525.log"
    metaeditor_log = tmp_path / "metaeditor.log"
    terminal_log.write_text("terminal", encoding="utf-8")
    metaeditor_log.write_text("compile", encoding="utf-8")

    assert newest_log(tmp_path) == terminal_log


def test_recent_logs_includes_previous_day_and_ignores_metaeditor(tmp_path):
    old_log = tmp_path / "20260524.log"
    prev_log = tmp_path / "20260525.log"
    current_log = tmp_path / "20260526.log"
    metaeditor_log = tmp_path / "metaeditor.log"
    old_log.write_text("old", encoding="utf-8")
    prev_log.write_text("prev heartbeat", encoding="utf-8")
    current_log.write_text("current startup", encoding="utf-8")
    metaeditor_log.write_text("compile", encoding="utf-8")

    logs = recent_logs(tmp_path)

    assert logs == [current_log, prev_log]
    assert combined_log_text(logs) == "prev heartbeat\ncurrent startup"
