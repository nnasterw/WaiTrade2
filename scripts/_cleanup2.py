#!/usr/bin/env python3
"""Cleanup: delete old backtest reports before June 5."""
import time
from pathlib import Path

MT5_ROOT = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')
CUTOFF = 1780617600  # June 5, 2026 00:00 UTC

deleted = deleted_size = kept = 0
for ext in ['htm', 'png']:
    for f in MT5_ROOT.glob(f'*.{ext}'):
        mtime = f.stat().st_mtime
        size = f.stat().st_size
        if mtime < CUTOFF:
            try:
                f.unlink()
                deleted += 1
                deleted_size += size
            except:
                pass
        else:
            kept += 1

print(f'Deleted: {deleted} ({deleted_size/1024/1024:.0f} MB)')
print(f'Kept: {kept}')
print(f'Done')
