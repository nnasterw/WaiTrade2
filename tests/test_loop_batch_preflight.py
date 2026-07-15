"""受控迭代回测前置检查测试。"""
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import _loop_batch


def test_prepare_strategy_accepts_error_zero_summary_with_warnings(monkeypatch, tmp_path):
    set_path = tmp_path / "mql5" / "Presets" / "demo.set"
    set_path.parent.mkdir(parents=True)
    set_path.write_text("InpVersion=DEMO\n", encoding="utf-8")
    calls = []

    def fake_run(cmd, timeout=120, env=None):
        calls.append(cmd)
        if "check_strategy_consistency.py" in str(cmd):
            return SimpleNamespace(returncode=0, stdout="ERROR: 0   WARN: 3   INFO: 2\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    monkeypatch.setattr(_loop_batch, "ROOT", tmp_path)
    monkeypatch.setattr(_loop_batch, "run_short", fake_run)
    monkeypatch.setattr(_loop_batch, "verify_ex5_provenance", lambda strategy, terminal: (True, "sha256=abc"))

    prepared, detail = _loop_batch.prepare_strategy("demo", tmp_path / "terminal")

    assert prepared is True
    assert "sha256=abc" in detail
    assert len(calls) == 3


def test_verify_ex5_provenance_checks_hash_and_source_freshness(monkeypatch, tmp_path):
    config = tmp_path / "config" / "strategies.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("defaults:\n  expert: WaiTrade2\\\\WaiTrade_OB\ndemo:\n  version: DEMO\n", encoding="utf-8")
    project_dir = tmp_path / "mql5" / "Experts" / "WaiTrade2"
    runtime_dir = tmp_path / "terminal" / "MQL5" / "Experts" / "WaiTrade2"
    project_dir.mkdir(parents=True)
    runtime_dir.mkdir(parents=True)
    source = project_dir / "WaiTrade_OB.mq5"
    project_ex5 = project_dir / "WaiTrade_OB.ex5"
    runtime_ex5 = runtime_dir / "WaiTrade_OB.ex5"
    source.write_text("source", encoding="utf-8")
    project_ex5.write_bytes(b"controlled")
    runtime_ex5.write_bytes(b"polluted")
    now = time.time()
    os.utime(source, (now - 10, now - 10))
    os.utime(project_ex5, (now, now))

    monkeypatch.setattr(_loop_batch, "ROOT", tmp_path)
    ok, detail = _loop_batch.verify_ex5_provenance("demo", tmp_path / "terminal")
    assert ok is False
    assert "来源不一致" in detail

    runtime_ex5.write_bytes(project_ex5.read_bytes())
    ok, detail = _loop_batch.verify_ex5_provenance("demo", tmp_path / "terminal")
    assert ok is True
    assert "sha256=" in detail

    os.utime(source, (now + 10, now + 10))
    ok, detail = _loop_batch.verify_ex5_provenance("demo", tmp_path / "terminal")
    assert ok is False
    assert "早于源码" in detail


def test_parse_backtest_stdout_accepts_compact_chinese_trade_count():
    balance, trades = _loop_batch.parse_backtest_stdout("结果: 14笔交易, 胜率64.3%, 余额$206.80")
    assert balance == 206.8
    assert trades == 14
