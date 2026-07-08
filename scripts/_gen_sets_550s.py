import sys, yaml
from pathlib import Path
ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set
yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
print("Loaded", len(config), "strategies")
strategies = ["v11-btc1-trend550", "v11-btc1-trend551", "v11-btc1-trend552", "v11-btc1-trend553"]
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
        import traceback
        print("  FAIL", s, str(e)[:200])
        traceback.print_exc()
print("Done")

