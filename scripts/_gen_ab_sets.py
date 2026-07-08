import sys, yaml
from pathlib import Path
ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set
yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
strategies = ["v11-btc1-yhcl1", "v11-btc1-yhcl2", "v11-btc1-loop1", "v11-btc1-loop2"]
out_dir = ROOT / "mql5" / "Presets"
for s in strategies:
    if s not in config:
        print("  Skip", s)
        continue
    out_path = out_dir / (s + ".set")
    if out_path.exists():
        print("  Exists", s)
        continue
    cfg = config[s]
    try:
        content = yaml_to_set.strategy_to_set(s, cfg)
        yaml_to_set.write_set(content, out_path)
        print("  Generated", s, "size:", out_path.stat().st_size)
    except Exception as e:
        print("  FAIL", s, str(e)[:200])
print("Done")

