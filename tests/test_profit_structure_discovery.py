"""盈利结构发现脚本的 campaign 分类回归测试。"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".agents" / "skills" / "wf-yhcl" / "scripts"))

from profit_structure_discovery import discover


def test_discovery_distinguishes_independent_reentry_from_addon(tmp_path):
    path = tmp_path / "trades.csv"
    fields = ["ticket", "time", "dir", "r", "pnl_proxy", "addon"]
    rows = [
        ["1", "2026-01-01 00:00:00", "buy", "1.0", "10", ""],
        ["2", "2026-01-01 01:00:00", "buy", "2.0", "20", ""],
        ["3", "2026-01-01 01:01:00", "buy", "-0.1", "-1", "True"],
        ["4", "2026-01-02 00:00:00", "sell", "-1.0", "-10", ""],
        ["5", "2026-01-02 01:00:00", "sell", "3.5", "35", ""],
        ["6", "2026-01-02 01:01:00", "sell", "-0.1", "-1", "True"],
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    result = discover(path)
    analysis = result["analysis"]
    assert analysis["later_independent"]["trades"] == 2
    assert analysis["later_addon"]["trades"] == 2
    assert analysis["post_win_independent"]["trades"] == 1
    assert analysis["post_loss_independent"]["trades"] == 1
    assert len(result["profit_structures"]) == 3
    assert result["profit_structures"][0]["id"] == "PS1"
