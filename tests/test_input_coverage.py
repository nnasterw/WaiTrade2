"""EA input 与 .set 显式覆盖测试。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def declared_names(path, pattern):
    text = Path(path).read_text(encoding="utf-8")
    return set(re.findall(pattern, text))


def test_loop161_set_explicitly_covers_all_slim_ea_inputs():
    v2 = declared_names(ROOT / "mql5/Include/WaiTrade2/Config.mqh", r"(?m)^\\s*(?:input|WT2_INPUT)\\s+\\S+\\s+(Inp\\w+)\\s*=")
    v3_ps1 = declared_names(ROOT / "mql5/Include/WaiTrade3/ConfigSMC.mqh", r"(?m)^\\s*WT3_PS1_INPUT\\s+\\S+\\s+(Inp\\w+)\\s*=")
    set_names = declared_names(ROOT / "mql5/Presets/v11-btc1-loop161.set", r"(?m)^(Inp\\w+)=")
    assert v2 <= set_names
    assert v3_ps1 <= set_names
    assert not (v2 | v3_ps1) - set_names


def test_yaml_map_covers_v2_declarations():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import yaml_to_set
    names = declared_names(ROOT / "mql5/Include/WaiTrade2/Config.mqh", r"(?m)^\\s*(?:input|WT2_INPUT)\\s+\\S+\\s+(Inp\\w+)\\s*=")
    assert names <= set(yaml_to_set.FLAT_MAP.values())
