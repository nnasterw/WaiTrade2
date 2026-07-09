"""Create bv1 strategy as alias for v11-btc1-loop43 (the 92.23 winner)"""
import sys, yaml
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))
import yaml_to_set

yaml_path = ROOT / "config" / "strategies.yaml"
with yaml_path.open("r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Get v11-btc1-loop43 as template
src_key = "v11-btc1-loop43"
if src_key not in config:
    print("ERROR: " + src_key + " not found in yaml")
    exit(1)

# Build bv1 entry - copy all parameters from loop43 but with new magic, version, name
src_cfg = dict(config[src_key])
# Override key fields
src_cfg["version"] = "V11-BTC1-BV1"
src_cfg["magic_number"] = 207001
src_cfg["description"] = "bv1 = v11-btc1-loop43 92.23 winner (SmartLock 1.8/0.5 + bad_bounce 0.22-0.28 + max_lot 1.0). Renamed production candidate."

# Add bv1 to config
config["v11-btc1-bv1"] = src_cfg
print("Added v11-btc1-bv1 to yaml")

# Write back
with yaml_path.open("w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000)
print("yaml updated, total strategies:", len(config))

# Generate .set
out_path = ROOT / "mql5" / "Presets" / "v11-btc1-bv1.set"
content = yaml_to_set.strategy_to_set("v11-btc1-bv1", config["v11-btc1-bv1"])
yaml_to_set.write_set(content, out_path)
print("Generated .set:", out_path, "size:", out_path.stat().st_size)

