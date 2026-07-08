import sys, yaml
from pathlib import Path
ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set
yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
strategies = ["v11-btc1-trend531", "v11-btc1-trend620", "v11-btc1-trend218", "v11-btc1-trend500", "v11-btc1-trend610"]
out_dir = ROOT / "mql5" / "Presets"
for s in strategies:
    out_path = out_dir / (s + ".set")
    if s in config:
        content = yaml_to_set.strategy_to_set(s, config[s])
        yaml_to_set.write_set(content, out_path)
        print("Regenerated", s)

