"""mt5_backtest_win — Windows 回测脚本行为测试

测试策略：通过公共接口（函数入参/返回值/副作用）验证行为，不测实现细节。
仅测 macOS 上也能运行的纯逻辑函数（INI生成、路径计算），
以及可通过 mock 隔离副作用的流程函数（kill、cache清理、run流程）。
"""
import importlib
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

# 设置假路径让 Windows 专属路径常量不报错
import os
os.environ.setdefault('MT5_HOME', r'C:\FakeMT5')
os.environ.setdefault('MT5_DATA', r'C:\FakeMT5Data')

import mt5_backtest_win as win


# ── INI 内容生成 ──────────────────────────────────────────────────────────────

BASE_CONFIG = {
    'backtest_defaults': {
        'period': 'M5', 'model': '4', 'deposit': 200,
        'currency': 'USD', 'leverage': '1:2000',
        'expert': r'WaiTrade2\WaiTrade_OB',
    },
    'mt5_account': {'login': '123', 'server': 'ICMarketsSC-Demo'},
    'v99g1': {'period': 'M5'},
}


def make_ini(strategy='v99g1', symbol='XAUUSDm',
             date_from='2026.01.01', date_to='2026.05.01'):
    with tempfile.TemporaryDirectory() as tmp:
        orig_ini_dir = win.INI_DIR
        win.INI_DIR = Path(tmp)
        try:
            ini_path = win.generate_ini(strategy, symbol, date_from, date_to, BASE_CONFIG)
            return ini_path.read_text(encoding='utf-8')
        finally:
            win.INI_DIR = orig_ini_dir


# ── 测试 1：INI 使用 MT5 标准键名 FromDate/ToDate（不是 DateFrom/DateTo）──
def test_ini_uses_fromdate_todate_keys():
    content = make_ini(date_from='2026.01.01', date_to='2026.05.01')
    assert 'FromDate=2026.01.01' in content
    assert 'ToDate=2026.05.01' in content
    assert 'DateFrom=' not in content
    assert 'DateTo=' not in content


# ── 测试 2：INI 包含 Currency 字段 ───────────────────────────────────────────
def test_ini_contains_currency():
    content = make_ini()
    assert 'Currency=USD' in content


# ── 测试 3：INI 有 [Common]+[Tester] 两个段（代理注入） ──────────────────────
def test_ini_has_common_and_tester_sections():
    content = make_ini()
    assert '[Common]' in content
    assert '[Tester]' in content
    assert 'ProxyEnable=' in content
    assert 'ProxyAddress=' in content


# ── 测试 4：INI Expert 字段正确 ──────────────────────────────────────────────
def test_ini_expert_field():
    content = make_ini()
    assert r'Expert=WaiTrade2\WaiTrade_OB' in content


# ── 测试 5：INI Symbol 字段正确 ──────────────────────────────────────────────
def test_ini_symbol_field():
    content = make_ini(symbol='BTCUSDm')
    assert 'Symbol=BTCUSDm' in content


# ── 测试 6：INI Leverage 处理 1:2000 格式（取后半部分） ──────────────────────
def test_ini_leverage_strips_ratio_prefix():
    content = make_ini()
    assert 'Leverage=2000' in content
    assert 'Leverage=1:2000' not in content


# ── 测试 7：INI ShutdownTerminal=1 ───────────────────────────────────────────
def test_ini_shutdown_terminal():
    content = make_ini()
    assert 'ShutdownTerminal=1' in content


# ── kill_mt5 存在且调用正确命令 ──────────────────────────────────────────────

def test_kill_mt5_exists():
    """kill_mt5 函数必须存在"""
    assert callable(getattr(win, 'kill_mt5', None)), \
        "mt5_backtest_win 缺少 kill_mt5() 函数"


def test_kill_mt5_uses_taskkill():
    """Windows 下必须用 taskkill 终止进程，不能用 pkill（Unix 专用）"""
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return MagicMock(returncode=0)

    with patch('mt5_backtest_win.subprocess.run', side_effect=fake_run):
        with patch('mt5_backtest_win.time.sleep'):
            win.kill_mt5()

    joined = ' '.join(' '.join(c) if isinstance(c, list) else c for c in calls)
    assert 'taskkill' in joined.lower(), \
        f"kill_mt5 应使用 taskkill，实际调用: {calls}"
    assert 'pkill' not in joined.lower(), \
        "kill_mt5 不应使用 pkill（Unix 专用）"


# ── clear_tester_cache 存在且清理目录内容 ───────────────────────────────────

def test_clear_tester_cache_exists():
    """clear_tester_cache 函数必须存在"""
    assert callable(getattr(win, 'clear_tester_cache', None)), \
        "mt5_backtest_win 缺少 clear_tester_cache() 函数"


def test_clear_tester_cache_removes_cache_contents():
    """clear_tester_cache 应清空 MT5_TESTER_DIR/cache 目录内容"""
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / 'cache'
        cache_dir.mkdir()
        (cache_dir / 'old_cache.bin').write_bytes(b'data')
        (cache_dir / 'another.tmp').write_bytes(b'data2')

        orig = win.MT5_TESTER_DIR
        win.MT5_TESTER_DIR = Path(tmp)
        try:
            win.clear_tester_cache()
        finally:
            win.MT5_TESTER_DIR = orig

        assert cache_dir.exists(), "cache 目录本身应保留（只清内容）"
        assert list(cache_dir.iterdir()) == [], "cache 目录内容应被清空"


def test_clear_tester_cache_noop_if_no_cache_dir():
    """cache 目录不存在时不应报错"""
    with tempfile.TemporaryDirectory() as tmp:
        orig = win.MT5_TESTER_DIR
        win.MT5_TESTER_DIR = Path(tmp)
        try:
            win.clear_tester_cache()  # 不应抛出异常
        finally:
            win.MT5_TESTER_DIR = orig


# ── run_mt5 冷启动流程 ───────────────────────────────────────────────────────

def test_run_mt5_calls_kill_before_start():
    """run_mt5 必须在启动 terminal64 之前先调用 kill_mt5()"""
    call_order = []

    fake_proc = MagicMock()
    fake_proc.poll.side_effect = [None, None, 0]
    fake_proc.returncode = 0

    with patch('mt5_backtest_win.kill_mt5', side_effect=lambda: call_order.append('kill')) as mock_kill, \
         patch('mt5_backtest_win.clear_tester_cache', side_effect=lambda: call_order.append('cache')), \
         patch('mt5_backtest_win.subprocess.Popen', side_effect=lambda *a, **kw: (call_order.append('popen'), fake_proc)[1]) as mock_popen, \
         patch('mt5_backtest_win.time.sleep'):
        win.run_mt5(timeout_sec=60)

    assert 'kill' in call_order, "run_mt5 必须调用 kill_mt5()"
    assert 'cache' in call_order, "run_mt5 必须调用 clear_tester_cache()"
    assert call_order.index('kill') < call_order.index('popen'), \
        "kill_mt5 必须在 Popen 之前调用"
    assert call_order.index('cache') < call_order.index('popen'), \
        "clear_tester_cache 必须在 Popen 之前调用"


def test_run_mt5_returns_true_on_exit_code_zero():
    """MT5 正常退出（returncode=0）时 run_mt5 应返回 True"""
    fake_proc = MagicMock()
    fake_proc.poll.side_effect = [None, 0]
    fake_proc.returncode = 0

    with patch('mt5_backtest_win.kill_mt5'), \
         patch('mt5_backtest_win.clear_tester_cache'), \
         patch('mt5_backtest_win.subprocess.Popen', return_value=fake_proc), \
         patch('mt5_backtest_win.time.sleep'):
        result = win.run_mt5(timeout_sec=60)

    assert result is True


def test_run_mt5_returns_false_on_nonzero_exit():
    """MT5 异常退出（returncode != 0）时 run_mt5 应返回 False"""
    fake_proc = MagicMock()
    fake_proc.poll.side_effect = [None, 1]
    fake_proc.returncode = 1

    with patch('mt5_backtest_win.kill_mt5'), \
         patch('mt5_backtest_win.clear_tester_cache'), \
         patch('mt5_backtest_win.subprocess.Popen', return_value=fake_proc), \
         patch('mt5_backtest_win.time.sleep'):
        result = win.run_mt5(timeout_sec=60)

    assert result is False


def test_run_mt5_returns_false_on_timeout():
    """MT5 超时时 run_mt5 应终止进程并返回 False"""
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None  # 始终未退出

    elapsed_calls = [0]

    def fake_sleep(_):
        elapsed_calls[0] += 100  # 每次sleep跳过100秒

    real_time = __import__('time').time
    start_time = real_time()

    with patch('mt5_backtest_win.kill_mt5'), \
         patch('mt5_backtest_win.clear_tester_cache'), \
         patch('mt5_backtest_win.subprocess.Popen', return_value=fake_proc), \
         patch('mt5_backtest_win.time.sleep', side_effect=fake_sleep), \
         patch('mt5_backtest_win.time.time', side_effect=lambda: start_time + elapsed_calls[0]):
        result = win.run_mt5(timeout_sec=30)

    assert result is False
    fake_proc.kill.assert_called_once()


# ── expert_ex5_path 路径计算 ─────────────────────────────────────────────────

def test_expert_ex5_path_simple():
    p = win.expert_ex5_path(Path(r'C:\MT5Data\MQL5\Experts'), r'WaiTrade2\WaiTrade_OB')
    assert p.suffix == '.ex5'
    assert 'WaiTrade_OB' in p.name


def test_expert_ex5_path_nested():
    experts_root = Path(r'C:\MT5Data\MQL5\Experts')
    p = win.expert_ex5_path(experts_root, r'WaiTrade2\WaiTrade_OB')
    assert p == experts_root / 'WaiTrade2' / 'WaiTrade_OB.ex5'
