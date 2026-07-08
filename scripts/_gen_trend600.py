import sys, yaml
from pathlib import Path
ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set
yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
s = "v11-btc1-trend600"
out_path = ROOT / "mql5" / "Presets" / (s + ".set")
cfg = config[s]
content = yaml_to_set.strategy_to_set(s, cfg)
yaml_to_set.write_set(content, out_path)
print("Generated", s, "size:", out_path.stat().st_size)

