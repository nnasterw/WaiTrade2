#!/usr/bin/env python3
"""Parse MT5 Tester log to extract EA Print() diagnostics."""
import re, sys
from pathlib import Path
from collections import defaultdict, Counter

LOG_PATH = Path(r'C:/Users/Gnef/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260606.log')

def parse_log():
    """Read the tester log and extract expert Print() output."""
    raw = LOG_PATH.read_bytes()

    # Try UTF-16-LE (typical for MT5 logs)
    try:
        text = raw.decode('utf-16-le')
    except:
        text = raw.decode('utf-16-le', errors='replace')

    lines = text.split('\n')
    print(f"Total lines: {len(lines)}")

    # Sample some lines to understand format
    expert_lines = []
    tester_lines = []
    other_sources = Counter()

    for i, line in enumerate(lines[:500000]):  # First 500K lines
        if not line.strip():
            continue
        # MT5 log format: 3-char code, tab, time, tab, source, tab, message
        parts = line.split('\t')
        if len(parts) >= 4:
            source = parts[2].strip()
            msg = '\t'.join(parts[3:])

            if 'Expert' in source or 'WaiTrade' in source or 'OB' in source:
                expert_lines.append((i, source, msg[:200]))
            elif 'Tester' in source:
                tester_lines.append((i, msg[:200]))
            else:
                other_sources[source] += 1

    print(f"\nSources found: {dict(other_sources.most_common(20))}")
    print(f"\nExpert lines: {len(expert_lines)}")
    print(f"Tester lines: {len(tester_lines)}")

    if expert_lines:
        print(f"\n--- First 30 Expert lines ---")
        for i, src, msg in expert_lines[:30]:
            print(f"[{i}] {src}: {msg[:150]}")

    if not expert_lines:
        # Search for FINAL_DIAG or any diagnostic pattern
        for pattern in ['FINAL_DIAG', 'TICK_NOISE', 'ENTRY', 'OB_', 'signal', 'Signal', 'entry', 'Entry']:
            count = 0
            for line in lines[:500000]:
                if pattern in line:
                    count += 1
            if count > 0:
                print(f"\n'{pattern}' found {count} times in first 500K lines")
                # Show a few examples
                examples = [l for l in lines[:500000] if pattern in l][:5]
                for e in examples:
                    print(f"  {e[:200]}")

        if all(count == 0 for pattern in ['FINAL_DIAG', 'TICK_NOISE', 'ENTRY', 'OB_']):
            print("\nNo EA diagnostic patterns found in first 500K lines.")
            print("Checking last 500K lines...")
            for pattern in ['FINAL_DIAG', 'TICK_NOISE', 'ENTRY', 'OB_']:
                count = sum(1 for l in lines[-500000:] if pattern in l)
                print(f"  '{pattern}' in last 500K: {count}")

if __name__ == '__main__':
    parse_log()
