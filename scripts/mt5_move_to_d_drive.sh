#!/bin/bash
# MT5 → D: 迁移脚本 (bash on Windows)
# 将回测数据目录和Tick数据从C:迁移到D:, 并用携版终端

set -e

C_BASES="/c/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/bases"
D_BASES="D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/bases"
D_PROFILE="D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/bases/Exness-MT5Trial5"
C_PROFILE="/c/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/bases/Exness-MT5Trial5"

echo "=== 1. 复制Exness Tick数据(1.1G) 到D: ==="
mkdir -p "$D_PROFILE"
time cp -r "$C_PROFILE/history" "$D_PROFILE/"
time cp -r "$C_PROFILE/ticks" "$D_PROFILE/"
# Optional: copy smaller metadata dirs
cp -r "$C_PROFILE/symbols" "$D_PROFILE/" 2>/dev/null
cp -r "$C_PROFILE/news" "$D_PROFILE/" 2>/dev/null
cp -r "$C_PROFILE/mail" "$D_PROFILE/" 2>/dev/null
cp -r "$C_PROFILE/trades" "$D_PROFILE/" 2>/dev/null
cp -r "$C_PROFILE/subscriptions" "$D_PROFILE/" 2>/dev/null
echo "  C: $C_PROFILE → D: $D_PROFILE 完成"

echo ""
echo "=== 2. 验证D:Tick数据 ==="
ls -lh "$D_PROFILE/history/XAUUSDm/" | head -5
du -sh "$D_PROFILE"

echo ""
echo "=== 3. 复制Default配置(110M) ==="
cp -r "$C_BASES/Default" "$D_BASES/" 2>/dev/null
echo "  完成"

echo ""
du -sh "$D_BASES"
echo ""
echo "=== 4. 输出MT5数据(可选, 已验证不需要) ==="
echo "  D:便携版终端路径: D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/terminal64.exe"
echo "  D:便携版数据目录: D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt/"
echo ""
echo "  设置环境变量后回测自动使用D:"
echo "  export MT5_HOME=\"D:/Code/codexProject/WaiTrade2/temp/mt5_portable_bt\""
echo "  export MT5_DATA=\"\$MT5_HOME\""
