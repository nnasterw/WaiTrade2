"""_loop_batch 晋级控制流测试，不启动 MT5。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import _loop_batch


def test_three_variants_promote_only_best_90d_to_720d(monkeypatch, tmp_path):
    terminal = tmp_path / "terminal"
    terminal.mkdir()
    output = tmp_path / "batch.json"
    calls = []
    balances = {"a": 210.0, "b": 250.0, "c": 230.0}

    monkeypatch.setattr(_loop_batch, "TEMP", tmp_path)
    monkeypatch.setattr(_loop_batch, "prepare_strategy", lambda strategy, terminal_path: (True, "set"))
    monkeypatch.setattr(_loop_batch, "clear_mt5_cache", lambda path: 0)

    def fake_run(strategy, terminal_path, env, stage, timeout=1200):
        calls.append((strategy, stage))
        report = tmp_path / (strategy + "_" + stage + ".txt")
        report.write_text("report", encoding="utf-8")
        return {
            "stage": stage,
            "success": True,
            "returncode": 0,
            "elapsed_sec": 1,
            "balance": balances[strategy] if stage == "validate_90d" else 205.0,
            "trades": 10,
            "report": str(report),
            "error_tail": "",
        }

    monkeypatch.setattr(_loop_batch, "run_mt5_test", fake_run)
    monkeypatch.setattr(_loop_batch, "extract_trades", lambda strategy, terminal_path, report: {
        "success": True,
        "original_report": report,
        "trades_csv": str(tmp_path / "trades.csv"),
        "monthly_csv": str(tmp_path / "24m.csv"),
        "wfys_json": str(tmp_path / "wfys.json"),
    })

    rc = _loop_batch.main([
        "--variants", "a,b,c",
        "--terminal", "terminal",
        "--workload-budget", "12",
        "--json-out", str(output),
    ])
    assert rc == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["promoted"] == "b"
    assert data["workload_used"] == 11.5
    assert sum(1 for _, stage in calls if stage == "smoke_30d") == 3
    assert sum(1 for _, stage in calls if stage == "validate_90d") == 3
    assert [(strategy, stage) for strategy, stage in calls if stage == "full_720d"] == [("b", "full_720d")]


def test_no_90d_survivor_skips_720d(monkeypatch, tmp_path):
    (tmp_path / "terminal").mkdir()
    calls = []
    monkeypatch.setattr(_loop_batch, "TEMP", tmp_path)
    monkeypatch.setattr(_loop_batch, "prepare_strategy", lambda strategy, terminal_path: (True, "set"))
    monkeypatch.setattr(_loop_batch, "clear_mt5_cache", lambda path: 0)

    def fake_run(strategy, terminal_path, env, stage, timeout=1200):
        calls.append(stage)
        return {
            "stage": stage,
            "success": stage == "smoke_30d",
            "returncode": 0,
            "elapsed_sec": 1,
            "balance": 200,
            "trades": 10 if stage == "smoke_30d" else 0,
            "report": None,
            "error_tail": "",
        }

    monkeypatch.setattr(_loop_batch, "run_mt5_test", fake_run)
    rc = _loop_batch.main(["--variants", "a,b", "--terminal", "terminal"])
    assert rc == 0
    assert "full_720d" not in calls


def test_more_than_three_variants_fails_before_terminal(monkeypatch, tmp_path):
    monkeypatch.setattr(_loop_batch, "TEMP", tmp_path)
    assert _loop_batch.main(["--variants", "a,b,c,d", "--terminal", "missing"]) == 2
