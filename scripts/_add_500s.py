import sys, yaml
from pathlib import Path

ROOT = Path("D:/Code/codexProject/WaiTrade2")
sys.path.insert(0, str(ROOT / "scripts"))

yaml_path = ROOT / "config" / "strategies.yaml"
with open(yaml_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
print("Loaded", len(config), "strategies")

# 先简单追加 trend500 测试 yaml.dump 是否能工作
config["v11-btc1-trend500"] = {
    "<<": "*v11_btc1_qual232",
    "version": "V11-BTC1-TREND500",
    "description": "trend500 = trend218 + cap_loss_hours 3,4,5,10,12",
    "magic_number": 206500,
    "btc_cap_loss_hours": "3,4,5,10,12",
}

# 用相同的参数 dump
with open(yaml_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=1000)
print("Wrote", len(config), "strategies")
import os
print("File size:", os.path.getsize(yaml_path))

