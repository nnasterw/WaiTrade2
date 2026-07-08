from pathlib import Path
yaml_path = Path("D:/Code/codexProject/WaiTrade2/config/strategies.yaml")
content = yaml_path.read_text(encoding="utf-8")
# For each v11-btc1-trendXXX, find the section and add enable_btc_profile: true
import re
variants = re.findall(r"v11-btc1-trend\d+:", content)
print("Found variants:", len(variants))
added = 0
for v in variants:
    vname = v[:-1]
    # Find the section bounds
    idx = content.find(v + chr(10))
    if idx < 0:
        continue
    # Find next variant
    next_idx = idx + 100
    # Find the next "v11-btc1-trend" or end
    rest = content[idx:]
    m = re.search(r"\nv11-btc1-(?:trend|qual|hold|geo)\w+:", rest[1:])
    if m:
        section_end = idx + 1 + m.start()
    else:
        section_end = idx + 500
    section = content[idx:section_end]
    if "enable_btc_profile" in section:
        continue
    # Find magic_number line and insert after it
    magic_match = re.search(r"  magic_number: \d+\n", section)
    if magic_match:
        insert_pos = idx + magic_match.end()
        new_line = "  enable_btc_profile: true\n"
        content = content[:insert_pos] + new_line + content[insert_pos:]
        added += 1
        print(f"  Added to {vname}")
yaml_path.write_text(content, encoding="utf-8")
print(f"Total added: {added}")

