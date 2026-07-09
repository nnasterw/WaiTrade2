import sys, yaml, re
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set

yaml_path = ROOT / "config" / "strategies.yaml"
content = yaml_path.read_text(encoding="utf-8")

# Find the bv1 section and parse it
match = re.search(r"v11-btc1-bv1:.*?(?=\nv11-btc1-|\Z)", content, re.DOTALL)
if not match:
    print("bv1 section not found")
    exit(1)

# Parse this section + qual232 anchor + defaults
# Load full yaml
config = yaml.safe_load(content)
if "v11-btc1-bv1" not in config:
    print("bv1 parse failed")
    exit(1)

cfg = config["v11-btc1-bv1"]
print("Loaded cfg:", list(cfg.keys()))

# Generate .set
out_path = ROOT / "mql5" / "Presets" / "v11-btc1-bv1.set"
yaml_to_set_content = yaml_to_set.strategy_to_set("v11-btc1-bv1", cfg)
yaml_to_set.write_set(yaml_to_set_content, out_path)
print("Generated:", out_path, "size:", out_path.stat().st_size)

