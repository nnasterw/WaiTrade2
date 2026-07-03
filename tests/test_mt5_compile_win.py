from __future__ import annotations

from scripts.mt5_compile_win import compile_command, parse_compile_log, sync_mql5_files


def test_parse_compile_log_accepts_zero_errors_with_nonzero_returncode(tmp_path):
    source = tmp_path / "EA.mq5"
    log = tmp_path / "EA.log"
    log.write_text("Result: 0 errors, 0 warnings, 2671 ms elapsed", encoding="utf-16-le")

    result = parse_compile_log(source, log, returncode=1)

    assert result.success is True
    assert result.returncode == 1
    assert result.warnings == 0


def test_parse_compile_log_rejects_errors(tmp_path):
    source = tmp_path / "EA.mq5"
    log = tmp_path / "EA.log"
    log.write_text("Result: 2 errors, 1 warnings, 100 ms elapsed", encoding="utf-16-le")

    result = parse_compile_log(source, log, returncode=0)

    assert result.success is False
    assert result.message == "2 errors"


def test_sync_mql5_files_copies_project_sources(tmp_path):
    mt5_data = tmp_path / "mt5"

    sync_mql5_files(mt5_data)

    assert (mt5_data / "MQL5" / "Experts" / "WaiTrade2" / "WaiTrade_OB.mq5").exists()
    assert (mt5_data / "MQL5" / "Experts" / "WaiTrade2" / "PortfolioSetup.mq5").exists()
    assert (mt5_data / "MQL5" / "Include" / "WaiTrade2" / "Config.mqh").exists()


def test_compile_command_uses_portable_data_dir(tmp_path):
    metaeditor = tmp_path / "MetaEditor64.exe"
    source = tmp_path / "MQL5" / "Experts" / "WaiTrade2" / "WaiTrade_OB.mq5"
    log = tmp_path / "compile.log"

    cmd = compile_command(metaeditor, source, log)

    assert "/portable" in cmd
    assert f"/compile:{source}" in cmd
    assert f"/log:{log}" in cmd
