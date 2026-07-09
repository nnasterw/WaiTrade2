import sys, yaml, time
from pathlib import Path
ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set
yaml_path = ROOT / "config" / "strategies.yaml"
t0 = time.time()
with yaml_path.open("r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
print(f"Loaded {len(config)} strategies in {time.time()-t0:.1f}s")
out_dir = ROOT / "mql5" / "Presets"
for s in ["v11-btc1-loop46", "v11-btc1-loop47", "v11-btc1-loop48", "v11-btc1-loop49", "v11-btc1-loop50"]:
    if s in config:
        c = yaml_to_set.strategy_to_set(s, config[s])
        p = out_dir / (s + ".set")
        yaml_to_set.write_set(c, p)
        print("Gen", s, p.stat().st_size)
    else:
        print("Missing:", s)