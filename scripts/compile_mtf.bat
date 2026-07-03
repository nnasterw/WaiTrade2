@echo off
set BT=D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt
set MQ5=%BT%\MQL5\Experts\WaiTrade2\WaiTrade_OB.mq5
set INC=%BT%\MQL5
set LOG=%BT%\compile_mtf.log

echo Compiling: %MQ5%
echo Include: %INC%
"%BT%\metaeditor64.exe" /compile:"%MQ5%" /inc:"%INC%" /log:"%LOG%"
echo Exit: %ERRORLEVEL%
type "%LOG%"
dir "%BT%\MQL5\Experts\WaiTrade2\WaiTrade_OB.ex5"
