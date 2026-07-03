from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import mt5_prepare_isolated_tester_win as prep


def touch_terminal(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "terminal64.exe").write_bytes(b"")
    (home / "metaeditor64.exe").write_bytes(b"")


def test_reject_live_path_rejects_live_root_and_parent():
    with pytest.raises(SystemExit):
        prep.reject_live_path(prep.LIVE_PORTABLE_ROOT)
    with pytest.raises(SystemExit):
        prep.reject_live_path(prep.LIVE_PORTABLE_ROOT.parent)


def test_validate_source_home_requires_terminal(tmp_path):
    with pytest.raises(SystemExit):
        prep.validate_source_home(tmp_path)


def test_validate_source_home_rejects_running_source(tmp_path):
    source = tmp_path / "source"
    touch_terminal(source)

    with patch("scripts.mt5_prepare_isolated_tester_win.terminal_processes_under", return_value=["1|terminal64|x"]):
        with pytest.raises(SystemExit):
            prep.validate_source_home(source)


def test_validate_destination_rejects_nested_source_dest(tmp_path):
    source = tmp_path / "source"
    touch_terminal(source)

    with pytest.raises(SystemExit):
        prep.validate_destination(source / "child", source)


def test_copy_portable_requires_force_for_existing_destination(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    touch_terminal(source)
    touch_terminal(dest)

    with pytest.raises(SystemExit):
        prep.copy_portable(source, dest, force=False)


def test_main_copies_source_to_isolated_destination(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    touch_terminal(source)
    (source / "MQL5").mkdir()

    with patch("scripts.mt5_prepare_isolated_tester_win.terminal_processes_under", return_value=[]):
        rc = prep.main(["--source-home", str(source), "--tester-home", str(dest)])

    assert rc == 0
    assert (dest / "terminal64.exe").exists()
    assert (dest / "metaeditor64.exe").exists()
    assert (dest / "MQL5").is_dir()


def test_terminal_processes_under_uses_directory_boundary():
    result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("scripts.mt5_prepare_isolated_tester_win.subprocess.run", return_value=result) as run:
        prep.terminal_processes_under(Path(r"C:\Tester"))

    joined = " ".join(run.call_args.args[0])
    assert "$rootWithSep" in joined
    assert run.call_args.kwargs["env"]["WAITRADE_MT5_PROCESS_ROOT"].lower().endswith("tester")
