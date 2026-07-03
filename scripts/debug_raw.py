import re
from pathlib import Path

DATA = Path(r'C:\Users\Gnef\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075')

for fname in ['phase2_mtf-off', 'p4_jan_off']:
    htm = DATA / f'{fname}.htm'
    raw = htm.read_bytes()
    html = raw.decode('utf-16-le', errors='replace')

    # Find first actual trade row (skip the balance row)
    # Look for row with XAUUSDm
    idx = html.find('XAUUSDm')
    if idx > 0:
        # Get the full <tr> containing this
        tr_start = html.rfind('<tr', 0, idx)
        tr_end = html.find('</tr>', idx)
        if tr_start >= 0 and tr_end > 0:
            tr_html = html[tr_start:tr_end+5]
            print(f"\n=== {fname}: First XAUUSDm row HTML ===")
            print(tr_html[:500])
            print("---")
            # Show all td tags
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_html, re.DOTALL)
            print(f"TD count: {len(tds)}")
            for i, td in enumerate(tds):
                print(f"  td[{i}]: {repr(td[:80])}")

    # Also find a row with non-zero profit
    import re
    # Find 'sl ' in comment (exit row)
    idx = html.find('sl ')
    if idx > 0:
        tr_start = html.rfind('<tr', 0, idx)
        tr_end = html.find('</tr>', idx)
        if tr_start >= 0 and tr_end > 0:
            tr_html = html[tr_start:tr_end+5]
            print(f"\n=== {fname}: First 'sl' exit row HTML ===")
            print(tr_html[:500])
            print("---")
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_html, re.DOTALL)
            print(f"TD count: {len(tds)}")
            for i, td in enumerate(tds):
                print(f"  td[{i}]: {repr(td[:80])}")
