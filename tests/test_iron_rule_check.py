"""Iron Rule 中性值与违规值测试。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".agents" / "skills" / "wf-yhcl" / "scripts"))

import iron_rule_check


def test_monthly_defensive_pos_mult_one_is_neutral():
    assert iron_rule_check.check_violations({"InpMonthlyDefensivePosMult": "1.0"}) == []


def test_monthly_defensive_pos_mult_below_one_is_violation():
    violations = iron_rule_check.check_violations({"InpMonthlyDefensivePosMult": "0.5"})
    assert len(violations) == 1
    assert violations[0]["key"] == "InpMonthlyDefensivePosMult"
