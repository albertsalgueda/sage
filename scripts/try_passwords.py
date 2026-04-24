#!/usr/bin/env python3
"""
Try passwords on the Sage VM Windows login screen via VNC.
The Sage VM is nested inside VMware Player on the GCP host.
VNC connects to the GCP host, showing VMware's window with the Sage VM inside.
"""
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

VNC_HOST = "34.175.32.149"
VNC_PORT = 5900
VNC_PASSWORD = "sage2026"
RESULTS_DIR = Path(__file__).parent.parent / "results" / "password_attempt"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

VENV_PYTHON = "/tmp/sage_venv/bin/python"

# Password candidates in order
PASSWORDS = ["admin", "1234", "Lortnoc", "Lortnoc2023+", "Sage2023", "sage200", ""]

def run_vnc_python(code: str):
    """Run Python code with VNC access in venv."""
    result = subprocess.run(
        [VENV_PYTHON, "-c", code],
        capture_output=True, text=True, timeout=30
    )
    return result

def take_screenshot(name: str):
    """Take a VNC screenshot and save it."""
    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(1)
client.screenshot('/tmp/vnc_shot.png')
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    if "OK" in r.stdout:
        import shutil
        dest = RESULTS_DIR / f"{name}.png"
        shutil.copy("/tmp/vnc_shot.png", dest)
        print(f"  Screenshot saved: {dest}")
        return True
    else:
        print(f"  Screenshot error: {r.stderr[:200]}")
        return False

def wake_screen():
    """Move mouse to wake the screen."""
    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(0.5)
client.mouseMove(960, 540)
time.sleep(0.3)
client.mouseMove(950, 530)
time.sleep(0.3)
client.mouseMove(960, 540)
time.sleep(1)
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    return "OK" in r.stdout

def click_vmware_window():
    """Click on the VMware window to give it focus."""
    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(0.5)
# Click in the middle of the screen where VMware window likely is
client.mousePress(1, 960, 540)
time.sleep(0.5)
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    return "OK" in r.stdout

def send_ctrl_alt_del():
    """Send Ctrl+Alt+Delete to unlock the Windows session inside VMware."""
    # VMware has a special way to send Ctrl+Alt+Delete to the guest
    # We need to use the VMware menu or special key sequence
    # In VMware Player, Ctrl+Alt+Insert sends Ctrl+Alt+Delete to guest
    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(0.5)

# Try Ctrl+Alt+Insert which VMware passes as Ctrl+Alt+Delete to guest
print("Sending Ctrl+Alt+Insert to VMware...")
client.keyDown('ctrl')
time.sleep(0.1)
client.keyDown('alt')
time.sleep(0.1)
client.keyDown('insert')
time.sleep(0.2)
client.keyUp('insert')
time.sleep(0.1)
client.keyUp('alt')
time.sleep(0.1)
client.keyUp('ctrl')
time.sleep(2)

client.screenshot('/tmp/after_cad.png')
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    if "OK" in r.stdout:
        import shutil
        shutil.copy("/tmp/after_cad.png", RESULTS_DIR / "after_ctrl_alt_del.png")
    print(f"  Ctrl+Alt+Del result: {r.stdout.strip()}")
    if r.stderr:
        print(f"  stderr: {r.stderr[:200]}")
    return "OK" in r.stdout

def type_password_and_enter(password: str):
    """Type a password into the focused field and press Enter."""
    # Escape the password for Python string
    safe_pw = password.replace("\\", "\\\\").replace("'", "\\'")

    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(0.5)

# Clear any existing text first (Ctrl+A then Delete)
client.keyDown('ctrl')
client.keyPress('a')
client.keyUp('ctrl')
time.sleep(0.2)
client.keyPress('delete')
time.sleep(0.2)

# Type the password
password = '{safe_pw}'
for char in password:
    client.keyPress(char)
    time.sleep(0.05)

time.sleep(0.3)
client.keyPress('enter')
time.sleep(3)

client.screenshot('/tmp/after_pw.png')
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    if "OK" in r.stdout:
        import shutil
        shutil.copy("/tmp/after_pw.png", RESULTS_DIR / f"after_pw_{password[:10]}.png")
    if r.stderr:
        print(f"  stderr: {r.stderr[:200]}")
    return "OK" in r.stdout

def click_password_field():
    """Click on the password field in the Windows login screen inside VMware."""
    # The VMware window is roughly centered. The Windows login screen
    # password field is typically in the lower-center of the VM display.
    # VMware Player window is ~1366x768 or similar inside the 1920x1080 host.
    # Let's click at approximately where the password field would be.
    code = f"""
import subprocess, sys
sys.path.insert(0, '/tmp/sage_venv/lib/python3.13/site-packages')
from vncdotool import api
import time

client = api.connect('{VNC_HOST}', password='{VNC_PASSWORD}', port={VNC_PORT})
time.sleep(0.5)

# Click in the center-ish of the screen where password field likely is
# The VM login screen is usually centered in VMware window
# Try clicking around center-bottom area
client.mousePress(1, 960, 600)
time.sleep(0.5)
client.mousePress(1, 960, 580)
time.sleep(0.5)
client.screenshot('/tmp/after_click_pw.png')
client.disconnect()
print("OK")
"""
    r = run_vnc_python(code)
    if "OK" in r.stdout:
        import shutil
        shutil.copy("/tmp/after_click_pw.png", RESULTS_DIR / "after_click_pw_field.png")
    return "OK" in r.stdout

def main():
    print(f"=== Password Try Script ===")
    print(f"Target: {VNC_HOST}:{VNC_PORT}")
    print(f"Results: {RESULTS_DIR}")
    print()

    # Step 1: Wake the screen
    print("1. Waking screen...")
    wake_screen()
    time.sleep(1)

    # Step 2: Take initial screenshot
    print("2. Taking initial screenshot...")
    take_screenshot("01_initial")

    # Step 3: Click VMware window to focus it
    print("3. Clicking VMware window...")
    click_vmware_window()
    time.sleep(0.5)

    # Step 4: Send Ctrl+Alt+Delete via Ctrl+Alt+Insert (VMware passthrough)
    print("4. Sending Ctrl+Alt+Delete to guest VM...")
    send_ctrl_alt_del()
    time.sleep(2)

    # Take screenshot after CAD
    take_screenshot("02_after_ctrl_alt_del")

    # Step 5: Click password field
    print("5. Clicking password field...")
    click_password_field()
    time.sleep(0.5)
    take_screenshot("03_after_click_pw_field")

    # Step 6: Try passwords
    print(f"\n6. Trying {len(PASSWORDS)} passwords...")
    for i, pw in enumerate(PASSWORDS):
        display_pw = pw if pw else "(empty)"
        print(f"  Trying password {i+1}/{len(PASSWORDS)}: '{display_pw}'")
        type_password_and_enter(pw)
        time.sleep(2)
        take_screenshot(f"04_pw_{i+1:02d}_{display_pw[:10]}")

    print(f"\nDone! Check screenshots in: {RESULTS_DIR}")

if __name__ == "__main__":
    main()
