$bt = "D:\Code\codexProject\WaiTrade2\temp\mt5_portable_bt"
$tests = @(
    @{Name="mtf-off"; Ini="mtf-off.ini"},
    @{Name="mtf-all"; Ini="mtf-all.ini"},
    @{Name="mtf-r5"; Ini="mtf-r5.ini"},
    @{Name="mtf-r4"; Ini="mtf-r4.ini"},
    @{Name="mtf-r1b"; Ini="mtf-r1b.ini"}
)

$results = @()

foreach ($t in $tests) {
    $name = $t.Name
    $ini = "$bt\Tester\$($t.Ini)"
    Write-Host "=== Running: $name ==="
    Write-Host "  INI: $ini"

    $proc = Start-Process -FilePath "$bt\terminal64.exe" `
        -ArgumentList "/config:`"$ini`"", "/portable" `
        -Wait -PassThru

    Write-Host "  Exit: $($proc.ExitCode)"

    # Check for report file
    $report = "$bt\Tester\${name}.txt"
    if (Test-Path $report) {
        $lines = Get-Content $report
        $balance = ($lines | Select-String "Final balance").ToString()
        $trades = ($lines | Select-String "Total trades").ToString()
        $pf = ($lines | Select-String "Profit Factor").ToString()
        Write-Host "  Report: $report"
        Write-Host "  $balance"
        Write-Host "  $trades"
        Write-Host "  $pf"
        $results += [PSCustomObject]@{Name=$name; Balance=$balance; Trades=$trades; PF=$pf}
    } else {
        Write-Host "  [WARN] No report found at $report"
    }
    Write-Host ""
}

Write-Host "=== Summary ==="
$results | Format-Table -AutoSize
