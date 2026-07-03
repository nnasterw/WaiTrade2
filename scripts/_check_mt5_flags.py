"""Check metatester64 CLI flags and terminal64 window modes."""
import subprocess, os, time

MT5 = r'C:\Program Files\MetaTrader 5'

# 1. metatester64 /? help
print("=== metatester64 /? ===")
r = subprocess.run([os.path.join(MT5, 'metatester64.exe'), '/?'],
    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
print('stdout:', r.stdout[:3000] if r.stdout else '(empty)')
print('stderr:', r.stderr[:3000] if r.stderr else '(empty)')
print()

# 2. terminal64 CLI flags
print("=== terminal64 /help ===")
r = subprocess.run([os.path.join(MT5, 'terminal64.exe'), '/help'],
    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
print('stdout:', r.stdout[:3000] if r.stdout else '(empty)')
print('stderr:', r.stderr[:3000] if r.stderr else '(empty)')
print()

# 3. Check if portable flag exists
print("=== terminal64 /? ===")
r = subprocess.run([os.path.join(MT5, 'terminal64.exe'), '/?'],
    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
print('stdout:', r.stdout[:3000] if r.stdout else '(empty)')
print('stderr:', r.stderr[:3000] if r.stderr else '(empty)')
print()

# 4. Check for SW_HIDE approach on terminal64
print("=== file info ===")
for name in ['terminal64.exe', 'metatester64.exe']:
    path = os.path.join(MT5, name)
    if os.path.exists(path):
        sz = os.path.getsize(path)
        print(f"  {name}: {sz:,} bytes")
    else:
        print(f"  {name}: NOT FOUND")
