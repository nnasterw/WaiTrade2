"""Regression test for _loop_batch token estimation (2026-07-13).

原因: 2026-07-13 诊断发现 _loop_batch.py 的 TOKEN_ESTIMATES 漏了 90d 中间验证场景,
导致估算高出实际 ~78% token。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from _loop_batch import (
    TOKEN_ESTIMATES,
    estimate_tokens_v2,
    measure_actual_tokens,
)


def test_token_estimates_has_90d():
    """TOKEN_ESTIMATES 必须包含 validate_90d 项 (Loop Engineering 主流 90d 中间验证)"""
    assert 'validate_90d' in TOKEN_ESTIMATES, "TOKEN_ESTIMATES 缺少 validate_90d 项 (2026-07-13 诊断跟踪)"
    assert TOKEN_ESTIMATES['validate_90d'] == 1.0, "validate_90d 应为 1.0M (90d 中间验证估算)"


def test_estimate_tokens_v2_smoke():
    """smoke_30d 阶段只计算 smoke"""
    est = estimate_tokens_v2('smoke_30d')
    assert est == 1.0, "smoke 阶段应为 1.0M"


def test_estimate_tokens_v2_validate_90d():
    """validate_90d 阶段只计算 90d"""
    est = estimate_tokens_v2('validate_90d')
    assert est == 1.0, "validate_90d 阶段应为 1.0M"


def test_estimate_tokens_v2_full_720d():
    """full_720d 阶段计算 smoke+720d+wfys 完整路径"""
    est = estimate_tokens_v2('full_720d')
    expected = 1.0 + 5.0 + 0.5
    assert est == expected, "full_720d 应为 " + str(expected) + "M, 实际 " + str(est) + "M"


def test_measure_actual_tokens_today():
    """2026-07-13 实测 token 用量复现性测试"""
    actual = measure_actual_tokens(r'results/backtest', '20260713')
    assert actual['n_720d'] == 4, "2026-07-13 应为 4 个 720d"
    assert actual['n_90d'] >= 20, "2026-07-13 应 >= 20 个 90d"
    assert actual['n_wfys'] >= 2, "2026-07-13 应 >= 2 个 wfys"
    assert 40 <= actual['est_token_m'] <= 55, "2026-07-13 实际 token 应在 40-55M"


def test_old_estimate_drift_warning():
    """旧估算与实际的偏移检查 - 验证 measure_actual_tokens 能捕捉 78% 偏差"""
    actual = measure_actual_tokens(r'results/backtest', '20260713')
    old_estimate = actual['files_count'] * 6.5
    assert old_estimate > actual['est_token_m'] * 1.5, (
        "老估算应明显高出实际 (原因 90d 未被统计), 老=" + str(old_estimate) + "M, 实际=" + str(actual['est_token_m']) + "M"
    )


if __name__ == '__main__':
    test_token_estimates_has_90d()
    print('PASS test_token_estimates_has_90d')
    test_estimate_tokens_v2_smoke()
    print('PASS test_estimate_tokens_v2_smoke')
    test_estimate_tokens_v2_validate_90d()
    print('PASS test_estimate_tokens_v2_validate_90d')
    test_estimate_tokens_v2_full_720d()
    print('PASS test_estimate_tokens_v2_full_720d')
    test_measure_actual_tokens_today()
    print('PASS test_measure_actual_tokens_today')
    test_old_estimate_drift_warning()
    print('PASS test_old_estimate_drift_warning')
    print('All regression tests passed (token estimation 2026-07-13)')