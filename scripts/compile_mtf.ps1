$bt = "D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt"
$p = Start-Process -FilePath "$bt\metaeditor64.exe" `
  -ArgumentList "/compile:`"$bt\MQL5\Experts\WaiTrade2\WaiTrade_OB.mq5`"",
                "/inc:`"$bt\MQL5`"",
                "/log:`"$bt\compile_mtf.log`"" `
  -Wait -PassThru
Write-Host "Exit: $($p.ExitCode)"
Get-Item "$bt\MQL5\Experts\WaiTrade2\WaiTrade_OB.ex5" | Select-Object Length, LastWriteTime
