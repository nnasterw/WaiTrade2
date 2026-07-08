from pathlib import Path
p = Path("D:/Code/codexProject/WaiTrade2/scripts/_loop_batch.py")
content = p.read_text(encoding="utf-8")
old_code = chr(34) + "Tester" + chr(34) + " / " + chr(34) + "Agent-127.0.0.1-3000" + chr(34) + " / " + chr(34) + "logs" + chr(34) + " / datetime.now().strftime(" + chr(34) + "%Y%m%d" + chr(34) + ") + " + chr(34) + ".log" + chr(34)
new_code = chr(34) + "Tester" + chr(34) + " / " + chr(34) + "Agent-127.0.0.1-3000" + chr(34) + " / " + chr(34) + "logs" + chr(34) + " / (datetime.now().strftime(" + chr(34) + "%Y%m%d" + chr(34) + ") + " + chr(34) + ".log" + chr(34) + ")"
if old_code in content:
    content = content.replace(old_code, new_code, 1)
    p.write_text(content, encoding="utf-8")
    print("Fixed")
else:
    print("Not found")

