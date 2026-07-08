import sys, yaml
from pathlib import Path
import subprocess

ROOT = Path("D:/Code/codexProject/WaiTrade2")
yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
print("Loaded", len(config), "strategies")

strategies = ["v11-btc1-trend500", "v11-btc1-trend501", "v11-btc1-trend502", "v11-btc1-trend503", "v11-btc1-trend504", "v11-btc1-trend505", "v11-btc1-trend506", "v11-btc1-trend507", "v11-btc1-trend508", "v11-btc1-trend509"]
out_dir = ROOT / "mql5" / "Presets"

for s in strategies:
    if s not in config:
        print("  Skip", s, "not in yaml")
        continue
    out_path = out_dir / (s + ".set")
    if out_path.exists():
        print("  Exists", s)
        continue
    cmd = [sys.executable, str(ROOT / "scripts" / "yaml_to_set.py"), s, "-o", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0 and out_path.exists():
        print("  Generated", s, "size:", out_path.stat().st_size)
    else:
        print("  FAIL", s, r.returncode, r.stderr[:200])
print("Done")

