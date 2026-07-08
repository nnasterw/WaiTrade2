"""为 Config.mqh 添加 BigWin 保护参数"""
from pathlib import Path

config_path = Path("D:/Code/codexProject/WaiTrade2/mql5/Include/WaiTrade2/Config.mqh")
content = config_path.read_text(encoding="utf-8")

# 查找锚点 (DTPResetPeakAfterPartial 行)
needle1 = "input bool   InpBTCDTPResetPeakAfterPartial = false;"

# 找到该行 (可能后面有中文注释)
import re
# 匹配该行整个 (从 InpBTCDTPResetPeakAfterPartial 开始到行尾)
pattern = re.compile(r"(input bool   InpBTCDTPResetPeakAfterPartial = false;[^\n]*)")
m = pattern.search(content)
if not m:
    print("Anchor not found!")
    exit(1)

old_line = m.group(1)
new_block = old_line + "\n" + """input double InpBTCBigWinTriggerR = 0.0;        // BTC 大赢单保护触发R (0=禁用)
input double InpBTCBigWinLockToR = 0.0;         // BTC 大赢单保护锁定到R (0=不锁)
input bool   InpBTCBigWinOnlyHTFTarget = true;  // 大赢单保护仅用于 HTF target 单
input bool   InpBTCEnableMonthlyLossGuard = false; // BTC 启用月度最大单笔损失强平 (0=禁用)
input double InpBTCMonthlyLossGuardR = -1.5;     // BTC 月度 max_loss 自动强平 R (负数)
input bool   InpBTCMonthlyLossGuardOnlyHTFTarget = true; // 月度 max_loss 仅支持 HTF target 单"""

content_new = content.replace(old_line, new_block, 1)
config_path.write_text(content_new, encoding="utf-8")
print("Inserted 6 new params after InpBTCDTPResetPeakAfterPartial")
print("File size:", config_path.stat().st_size)

