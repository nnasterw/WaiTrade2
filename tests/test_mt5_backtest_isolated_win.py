from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import mt5_backtest_isolated_win as isolated


def test_validate_tester_home_rejects_live_portable_root():
    with pytest.raises(SystemExit):
        isolated.validate_tester_home(isolated.LIVE_PORTABLE_ROOT)


def test_validate_tester_home_rejects_live_portable_parent():
    with pytest.raises(SystemExit):
        isolated.validate_tester_home(isolated.LIVE_PORTABLE_ROOT.parent)


def test_validate_tester_home_requires_terminal(tmp_path):
    with pytest.raises(SystemExit):
        isolated.validate_tester_home(tmp_path)


def test_main_sets_isolated_environment_and_forwards_args(tmp_path):
    tester_home = tmp_path / "tester"
    tester_home.mkdir()
    (tester_home / "terminal64.exe").write_bytes(b"")

    with patch("scripts.mt5_backtest_isolated_win.run_live_guard") as guard, \
         patch("scripts.mt5_backtest_isolated_win.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        rc = isolated.main(
            [
                "--tester-home",
                str(tester_home),
                "--",
                "--strategy",
                "v1",
                "--symbol",
                "BTCUSDm",
                "--days",
                "1",
            ]
        )

    assert rc == 0
    assert [call.args[0] for call in guard.call_args_list] == ["before", "after"]
    cmd = run.call_args.args[0]
    env = run.call_args.kwargs["env"]
    assert cmd[0] == sys.executable
    assert cmd[-6:] == ["--strategy", "v1", "--symbol", "BTCUSDm", "--days", "1"]
    assert env["MT5_HOME"] == str(tester_home.resolve())
    assert env["MT5_DATA"] == str(tester_home.resolve())
    assert env["MT5_PORTABLE"] == "1"


def test_main_refuses_backtest_when_live_guard_fails(tmp_path):
    tester_home = tmp_path / "tester"
    tester_home.mkdir()
    (tester_home / "terminal64.exe").write_bytes(b"")

    with patch("scripts.mt5_backtest_isolated_win.run_live_guard", side_effect=SystemExit("bad live")), \
         patch("scripts.mt5_backtest_isolated_win.subprocess.run") as run:
        with pytest.raises(SystemExit):
            isolated.main(["--tester-home", str(tester_home), "--", "--strategy", "v1"])

    run.assert_not_called()


def test_main_runs_after_guard_even_when_backtest_fails(tmp_path):
    tester_home = tmp_path / "tester"
    tester_home.mkdir()
    (tester_home / "terminal64.exe").write_bytes(b"")

    with patch("scripts.mt5_backtest_isolated_win.run_live_guard") as guard, \
         patch("scripts.mt5_backtest_isolated_win.subprocess.run") as run:
        run.return_value = MagicMock(returncode=7)
        rc = isolated.main(["--tester-home", str(tester_home), "--", "--strategy", "v1"])

    assert rc == 7
    assert [call.args[0] for call in guard.call_args_list] == ["before", "after"]


def test_run_live_guard_requires_passing_live_status():
    good = MagicMock(returncode=0, stdout="# Portfolio live status\n\nstreams=7 pass=true\n", stderr="")
    with patch("scripts.mt5_backtest_isolated_win.subprocess.run", return_value=good) as run:
        isolated.run_live_guard("before")

    cmd = run.call_args.args[0]
    assert "portfolio_live_status.py" in cmd[1]
    assert "--max-heartbeat-age-min" in cmd


def test_run_live_guard_exits_on_failed_live_status():
    bad = MagicMock(returncode=1, stdout="# Portfolio live status\n\nstreams=7 pass=false\n", stderr="")
    with patch("scripts.mt5_backtest_isolated_win.subprocess.run", return_value=bad):
        with pytest.raises(SystemExit):
            isolated.run_live_guard("before")
