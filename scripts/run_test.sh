#!/bin/bash
# D1-D6 backtest runner — direct .set manipulation, MT5 Model 4
set -e

MT5_HOME="/c/Program Files/MetaTrader 5"
MT5_DATA="$APPDATA/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075"
SET_DIR="$MT5_DATA/MQL5/Profiles/Tester"
INI_FILE="$MT5_DATA/Tester/backtest.ini"
REPORT_DIR="results/backtest"

# Copy base QS3 set
BASE_SET="mql5/Presets/V11XAU-QS3.set"

run_one() {
    local name=$1 from=$2 to=$3
    local set_file="$SET_DIR/${name}.set"
    local report_name="${name}_${from//./}_${to//./}"

    # Copy and modify set
    cp "$BASE_SET" "$set_file"
    shift 3
    for pair in "$@"; do
        key="${pair%%=*}"
        val="${pair#*=}"
        sed -i "s|^${key}=.*|${key}=${val}|" "$set_file"
    done

    # Write INI
    cat > "$INI_FILE" << EOFINI
[Common]
Login=
Server=

[Tester]
Expert=WaiTrade2\\WaiTrade_OB
ExpertParameters=${name}.set
Symbol=XAUUSDm
Period=M1
Model=4
Optimization=0
FromDate=${from}
ToDate=${to}
Deposit=200
Currency=USD
Leverage=2000
ExecutionMode=0
ShutdownTerminal=1
Report=${report_name}
EOFINI

    # Kill backtest MT5 only (not live portable terminals)
    powershell -Command "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like '*Program Files*' } | Stop-Process -Force" 2>/dev/null
    sleep 3

    # Run
    "$MT5_HOME/terminal64.exe" "/config:$INI_FILE" &

    # Wait for completion
    for i in $(seq 1 60); do
        sleep 5
        if ! powershell -Command "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like '*Program Files*' }).Count" 2>/dev/null | grep -q "0"; then
            # Still running
            continue
        fi
        break
    done
    sleep 3

    # Parse HTML report
    local html=$(ls -t "$MT5_DATA/Tester/"*.htm 2>/dev/null | head -1)
    if [ -n "$html" ]; then
        local result=$(grep -oP 'XAUUSDm.*?\d+\s+[\d.]+\s+[\d.]+\s+.*?\$\d+\.\d+' "$html" 2>/dev/null | head -1)
        echo "  $name ($from~$to): $result"
    else
        echo "  $name ($from~$to): NO REPORT"
    fi
}

echo "=== D1: Bounce Gradient ==="
run_one "V11XAU-QS3-D1A" "2026.06.02" "2026.06.03" \
    "InpVersion=V11XAU-QS3-D1A" "InpMagicNumber=204879" \
    "InpBouncePct=0.22" "InpBounceSweetMinPct=0.26" "InpOutsideBounceSweetMult=0.5"
run_one "V11XAU-QS3-D1A" "2025.05.28" "2025.05.30" \
    "InpVersion=V11XAU-QS3-D1A" "InpMagicNumber=204879" \
    "InpBouncePct=0.22" "InpBounceSweetMinPct=0.26" "InpOutsideBounceSweetMult=0.5"

echo "=== D1B ==="
run_one "V11XAU-QS3-D1B" "2026.06.02" "2026.06.03" \
    "InpVersion=V11XAU-QS3-D1B" "InpMagicNumber=204878" \
    "InpBouncePct=0.30" "InpBounceSweetMinPct=0.35" "InpOutsideBounceSweetMult=0.4"

echo "=== D1C ==="
run_one "V11XAU-QS3-D1C" "2026.06.02" "2026.06.03" \
    "InpVersion=V11XAU-QS3-D1C" "InpMagicNumber=204877" \
    "InpBouncePct=0.40" "InpBounceSweetMinPct=0.40" "InpOutsideBounceSweetMult=0.3"

echo "Done"
