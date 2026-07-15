"""BV1 专用 v3 编译的 MT5 input 预算测试。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count_direct_inputs(path):
    text = Path(path).read_text(encoding="utf-8")
    return len(re.findall(r"(?m)^\s*s?input\s+(?!group\b)", text))


def test_bv1_slim_wrapper_keeps_public_inputs_under_mt5_limit():
    wrapper = ROOT / "mql5" / "Experts" / "WaiTrade3" / "WaiTrade_OB_BV1_Slim.mq5"
    smc_config = ROOT / "mql5" / "Include" / "WaiTrade3" / "ConfigSMC.mqh"
    smc_main = ROOT / "mql5" / "Experts" / "WaiTrade3" / "WaiTrade_OB_SMC.mq5"
    base_config = ROOT / "mql5" / "Include" / "WaiTrade2" / "Config.mqh"
    assert "#define WAITRADE3_BV1_SLIM" in wrapper.read_text(encoding="utf-8")
    assert count_direct_inputs(smc_config) == 0
    assert count_direct_inputs(smc_main) == 0
    assert smc_config.read_text(encoding="utf-8").count("WT3_INPUT ") >= 166
    assert count_direct_inputs(base_config) <= 1024
