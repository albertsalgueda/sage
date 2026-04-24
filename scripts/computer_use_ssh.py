"""
Computer-Use controller via SSH + PowerShell scheduled tasks.

Instead of VNC (which has auth/black-screen issues on Windows Server),
this controller uses:
  1. SSH to upload PowerShell scripts to the GCP host
  2. Scheduled tasks to run them in the interactive console session
  3. SCP to download screenshots
  4. Anthropic's computer-use API for vision + action planning

Architecture:
    Python (local Mac)
      → SSH → GCP Windows Server (sage-vm)
        → Scheduled Task runs PowerShell in console session
          → PowerShell captures screenshots / sends mouse+keyboard
            → VMware Player window → Sage 200 VM

Requirements:
    pip install anthropic Pillow paramiko
    SSH key at ~/.ssh/google_compute_engine

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    export SAGE_VM_IP=34.175.32.149

    python computer_use_ssh.py                    # Navigate Sage admin console
    python computer_use_ssh.py --create-table     # Create CF_Equipos table
    python computer_use_ssh.py --custom "..."     # Custom task
"""

import anthropic
import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

SAGE_VM_IP = os.environ.get("SAGE_VM_IP", "34.175.32.149")
SSH_KEY = os.path.expanduser("~/.ssh/google_compute_engine")
SSH_USER = "albert"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

RESULTS_DIR = Path(__file__).parent.parent / "results" / "computer_use"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "claude-sonnet-4-6-20250514"


# ─── SSH helpers ────────────────────────────────────────────────────────────

def ssh_cmd(command: str, timeout: int = 30) -> str:
    """Run a command on the GCP host via SSH."""
    result = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
         "-i", SSH_KEY, f"{SSH_USER}@{SAGE_VM_IP}", command],
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout + result.stderr


def scp_download(remote_path: str, local_path: str, timeout: int = 30):
    """Download a file from the GCP host."""
    subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-i", SSH_KEY,
         f"{SSH_USER}@{SAGE_VM_IP}:{remote_path}", local_path],
        capture_output=True, timeout=timeout
    )


def scp_upload(local_path: str, remote_path: str, timeout: int = 30):
    """Upload a file to the GCP host."""
    subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-i", SSH_KEY,
         local_path, f"{SSH_USER}@{SAGE_VM_IP}:{remote_path}"],
        capture_output=True, timeout=timeout
    )


def run_in_interactive_session(ps_script: str, task_name: str = "CUAction",
                                timeout: int = 30) -> bool:
    """Upload and run a PowerShell script in the interactive console session."""
    # Write script to temp file
    local_tmp = "/tmp/cu_action.ps1"
    with open(local_tmp, "w", encoding="utf-8") as f:
        f.write(ps_script)

    # Upload
    scp_upload(local_tmp, "C:/cu_action.ps1")

    # Create and run scheduled task
    ssh_cmd(
        f'schtasks /create /tn {task_name} /tr '
        f'"powershell -ExecutionPolicy Bypass -File C:\\cu_action.ps1" '
        f'/sc once /st 00:00 /ru {SSH_USER} /rl highest /it /f'
    )
    result = ssh_cmd(f'schtasks /run /tn {task_name}')
    return "SUCCESS" in result


# ─── PowerShell script templates ────────────────────────────────────────────

PS_SCREENSHOT = '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''

PS_CLICK_TEMPLATE = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CUMouse {{
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint f, int x, int y, uint d, IntPtr e);
    public const uint LDOWN = 0x0002;
    public const uint LUP = 0x0004;
    public const uint RDOWN = 0x0008;
    public const uint RUP = 0x0010;
    public const uint MDOWN = 0x0020;
    public const uint MUP = 0x0040;
}}
"@
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})
Start-Sleep -Milliseconds 100
[CUMouse]::mouse_event([CUMouse]::{down_flag}, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 50
[CUMouse]::mouse_event([CUMouse]::{up_flag}, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 300

# Take screenshot after action
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''

PS_TYPE_TEMPLATE = '''
Add-Type -AssemblyName System.Windows.Forms
# Type text using SendKeys
$text = '{text}'
foreach ($char in $text.ToCharArray()) {{
    $key = [string]$char
    if ($key -match '[+^%~(){{}}]') {{ $key = "{{$key}}" }}
    [System.Windows.Forms.SendKeys]::SendWait($key)
    Start-Sleep -Milliseconds 30
}}
Start-Sleep -Milliseconds 300

# Take screenshot
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''

PS_KEY_TEMPLATE = '''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("{sendkeys_code}")
Start-Sleep -Milliseconds 500

# Take screenshot
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''

PS_DOUBLE_CLICK_TEMPLATE = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CUMouse2 {{
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint f, int x, int y, uint d, IntPtr e);
    public const uint LDOWN = 0x0002;
    public const uint LUP = 0x0004;
}}
"@
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})
Start-Sleep -Milliseconds 100
[CUMouse2]::mouse_event([CUMouse2]::LDOWN, 0, 0, 0, [IntPtr]::Zero)
[CUMouse2]::mouse_event([CUMouse2]::LUP, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 100
[CUMouse2]::mouse_event([CUMouse2]::LDOWN, 0, 0, 0, [IntPtr]::Zero)
[CUMouse2]::mouse_event([CUMouse2]::LUP, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 300

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''

PS_SCROLL_TEMPLATE = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CUScroll {{
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint f, int x, int y, uint d, IntPtr e);
    public const uint WHEEL = 0x0800;
}}
"@
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})
Start-Sleep -Milliseconds 100
# Positive = up, negative = down. Each "click" is 120 units.
[CUScroll]::mouse_event([CUScroll]::WHEEL, 0, 0, {delta}, [IntPtr]::Zero)
Start-Sleep -Milliseconds 300

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''


# ─── SSHController ──────────────────────────────────────────────────────────

class SSHController:
    """Controls the remote desktop via SSH + PowerShell scheduled tasks."""

    # Map Anthropic key names to SendKeys codes
    KEY_MAP = {
        "Return": "{ENTER}", "Tab": "{TAB}", "Escape": "{ESC}",
        "BackSpace": "{BACKSPACE}", "Delete": "{DELETE}", "space": " ",
        "Up": "{UP}", "Down": "{DOWN}", "Left": "{LEFT}", "Right": "{RIGHT}",
        "Home": "{HOME}", "End": "{END}", "Page_Up": "{PGUP}", "Page_Down": "{PGDN}",
        "F1": "{F1}", "F2": "{F2}", "F3": "{F3}", "F4": "{F4}",
        "F5": "{F5}", "F6": "{F6}", "F7": "{F7}", "F8": "{F8}",
        "F9": "{F9}", "F10": "{F10}", "F11": "{F11}", "F12": "{F12}",
        "Insert": "{INSERT}",
    }

    def __init__(self):
        self.action_delay = 1.5  # seconds to wait after running action

    def screenshot(self, save_path: str = None) -> bytes:
        """Take screenshot via SSH scheduled task, download, return PNG bytes."""
        run_in_interactive_session(PS_SCREENSHOT, "CUScreenshot")
        time.sleep(self.action_delay)

        local_path = save_path or str(RESULTS_DIR / "cu_screenshot.png")
        scp_download("C:/cu_screenshot.png", local_path)

        with open(local_path, "rb") as f:
            return f.read()

    def click(self, x: int, y: int, button: str = "left"):
        """Click at coordinates."""
        if button == "right":
            down_flag, up_flag = "RDOWN", "RUP"
        elif button == "middle":
            down_flag, up_flag = "MDOWN", "MUP"
        else:
            down_flag, up_flag = "LDOWN", "LUP"

        script = PS_CLICK_TEMPLATE.format(x=x, y=y,
                                           down_flag=down_flag, up_flag=up_flag)
        run_in_interactive_session(script, "CUClick")
        time.sleep(self.action_delay)

    def double_click(self, x: int, y: int):
        """Double-click at coordinates."""
        script = PS_DOUBLE_CLICK_TEMPLATE.format(x=x, y=y)
        run_in_interactive_session(script, "CUDblClick")
        time.sleep(self.action_delay)

    def type_text(self, text: str):
        """Type text string."""
        # Escape single quotes for PowerShell
        safe_text = text.replace("'", "''")
        script = PS_TYPE_TEMPLATE.format(text=safe_text)
        run_in_interactive_session(script, "CUType")
        time.sleep(self.action_delay)

    def press_key(self, key: str):
        """Press a special key or key combination."""
        sendkeys_code = self.KEY_MAP.get(key, key)
        script = PS_KEY_TEMPLATE.format(sendkeys_code=sendkeys_code)
        run_in_interactive_session(script, "CUKey")
        time.sleep(self.action_delay)

    def scroll(self, x: int, y: int, direction: str, amount: int = 3):
        """Scroll at coordinates."""
        # 120 per click, negative = down
        delta = 120 * amount if direction == "up" else -(120 * amount)
        script = PS_SCROLL_TEMPLATE.format(x=x, y=y, delta=delta)
        run_in_interactive_session(script, "CUScroll")
        time.sleep(self.action_delay)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Drag from start to end."""
        script = f'''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CUDrag {{
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint f, int x, int y, uint d, IntPtr e);
    public const uint LDOWN = 0x0002;
    public const uint LUP = 0x0004;
    public const uint MOVE = 0x0001;
}}
"@
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({start_x}, {start_y})
Start-Sleep -Milliseconds 200
[CUDrag]::mouse_event([CUDrag]::LDOWN, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 100

# Smooth drag
$steps = 10
for ($i = 1; $i -le $steps; $i++) {{
    $px = {start_x} + (({end_x} - {start_x}) * $i / $steps)
    $py = {start_y} + (({end_y} - {start_y}) * $i / $steps)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point([int]$px, [int]$py)
    Start-Sleep -Milliseconds 30
}}

Start-Sleep -Milliseconds 100
[CUDrag]::mouse_event([CUDrag]::LUP, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 300

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("C:\\cu_screenshot.png")
$graphics.Dispose()
$bitmap.Dispose()
'''
        run_in_interactive_session(script, "CUDrag")
        time.sleep(self.action_delay)


# ─── Action executor ────────────────────────────────────────────────────────

def execute_action(controller: SSHController, action: dict):
    """Execute a computer-use action."""
    action_type = action.get("action", action.get("type", "unknown"))

    if action_type == "screenshot":
        return  # Handled by the loop

    elif action_type == "left_click":
        x, y = action["coordinate"]
        controller.click(x, y, "left")

    elif action_type == "right_click":
        x, y = action["coordinate"]
        controller.click(x, y, "right")

    elif action_type == "double_click":
        x, y = action["coordinate"]
        controller.double_click(x, y)

    elif action_type == "middle_click":
        x, y = action["coordinate"]
        controller.click(x, y, "middle")

    elif action_type == "mouse_move":
        x, y = action["coordinate"]
        # Just move cursor (no click)
        run_in_interactive_session(f'''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})
''', "CUMove")

    elif action_type == "left_click_drag":
        sx, sy = action["start_coordinate"]
        ex, ey = action["coordinate"]
        controller.drag(sx, sy, ex, ey)

    elif action_type == "type":
        controller.type_text(action["text"])

    elif action_type == "key":
        controller.press_key(action["key"])

    elif action_type == "scroll":
        x, y = action["coordinate"]
        direction = action.get("scroll_direction", "down")
        amount = action.get("scroll_amount", 3)
        controller.scroll(x, y, direction, amount)

    else:
        print(f"  ⚠ Unknown action: {action_type}")


# ─── Computer-Use Loop ──────────────────────────────────────────────────────

def run_computer_use_loop(controller: SSHController, task: str,
                          max_steps: int = 30):
    """
    Main computer-use loop:
      1. Take screenshot via SSH+PowerShell
      2. Send to Claude with computer-use tool
      3. Claude returns action (click, type, etc.)
      4. Execute action via SSH+PowerShell
      5. Repeat until done or max_steps
    """
    client = anthropic.Anthropic()
    log_entries = []
    step = 0

    print(f"\n{'='*60}")
    print(f"  Computer-Use Task (SSH mode)")
    print(f"{'='*60}")
    print(f"  {task[:200]}...")
    print(f"{'='*60}\n")

    messages = [
        {"role": "user", "content": [{"type": "text", "text": task}]}
    ]
    last_tool_use_id = None

    while step < max_steps:
        step += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(RESULTS_DIR / f"step_{step:03d}_{timestamp}.png")

        # 1. Take screenshot
        print(f"\n--- Step {step}/{max_steps} ---")
        print("Taking screenshot via SSH...")
        try:
            png_bytes = controller.screenshot(screenshot_path)
            if len(png_bytes) < 1000:
                print(f"  Warning: screenshot too small ({len(png_bytes)} bytes)")
                continue
            screenshot_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            print(f"  Saved: {screenshot_path} ({len(png_bytes)} bytes)")
        except Exception as e:
            print(f"  Screenshot failed: {e}")
            break

        # 2. Build message with screenshot
        if step > 1 and last_tool_use_id:
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": last_tool_use_id,
                    "content": [{
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64
                        }
                    }]
                }]
            })
        else:
            messages[0]["content"].append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64
                }
            })

        # 3. Ask Claude
        print("Asking Claude to analyze...")
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=[{
                    "type": "computer_20251124",
                    "name": "computer",
                    "display_width_px": SCREEN_WIDTH,
                    "display_height_px": SCREEN_HEIGHT,
                    "display_number": 0,
                }],
                messages=messages,
                betas=["computer-use-2025-01-24"],
            )
        except Exception as e:
            print(f"  API error: {e}")
            log_entries.append({
                "step": step, "timestamp": timestamp,
                "action": "api_error", "error": str(e),
            })
            break

        # 4. Process response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            for block in assistant_content:
                if hasattr(block, "text"):
                    print(f"\n  Claude: {block.text}")
            print("\n  Task completed.")
            log_entries.append({
                "step": step, "timestamp": timestamp,
                "action": "end_turn",
            })
            break

        # 5. Execute tool-use actions
        for block in assistant_content:
            if hasattr(block, "text") and block.text:
                print(f"  Claude: {block.text}")

            if block.type == "tool_use":
                last_tool_use_id = block.id
                action = block.input
                action_type = action.get("action", "?")

                coord = action.get("coordinate", "")
                text = action.get("text", "")[:40]
                print(f"  Action: {action_type}", end="")
                if coord:
                    print(f" @ {coord}", end="")
                if text:
                    print(f" '{text}'", end="")
                print()

                log_entries.append({
                    "step": step, "timestamp": timestamp,
                    "action": action_type,
                    "details": {k: v for k, v in action.items()
                               if k not in ("type", "action")},
                })

                if action_type != "screenshot":
                    try:
                        execute_action(controller, action)
                    except Exception as e:
                        print(f"  Action failed: {e}")

    # Save log
    log_path = RESULTS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w") as f:
        json.dump({
            "task": task,
            "vm_ip": SAGE_VM_IP,
            "model": MODEL,
            "mode": "ssh",
            "steps": log_entries,
            "total_steps": step,
        }, f, indent=2)

    print(f"\nLog saved: {log_path}")
    return log_entries


# ─── Task definitions ───────────────────────────────────────────────────────

TASK_NAVIGATE = """
You are controlling a Windows desktop that shows VMware Player with a Sage 200 VM.
The interface is in Spanish. The VMware Player window shows the Sage 200 VM inside.

Your task:
1. Look at the current screen and describe what you see.
2. If the VM shows a login screen, the username is "Administrador".
3. If you see the Windows desktop inside the VM, find the Sage 200 application.
4. Navigate to: Consola de Administración
5. Once there, describe what you see.

Take your time. Describe what you see before acting.
"""

TASK_CREATE_TABLE = """
You are controlling a Windows desktop with Sage 200's development environment.
The VMware Player window shows the Sage 200 VM. The interface is in Spanish.

Your task is to create a new table in Sage 200:

Table: CF_Equipos
Fields:
  - CodigoEquipo (Character, 5 chars, Primary Key)
  - Nombre (Character, 50 chars)
  - JuegaEuropa (Boolean / Lógico)
  - Competicion (Character, 30 chars)

Steps:
1. Open Sage 200's Consola de Administración
2. Navigate to create/modify tables
3. Create CF_Equipos with all fields above
4. Save the table

Describe what you see at each step.
"""

TASK_EXPORT_DAT = """
You are controlling Sage 200's Consola de Administración.
The interface is in Spanish.

Your task is to export all CF_ objects as a .dat file:

1. Go to Herramientas → Exportar Objetos de Repositorio
2. Select all objects with the CF_ prefix (CF_Equipos, CF_Resultados, CF_Clasificacion)
3. Export them to a .dat file
4. Tell me where the file was saved

Describe each step.
"""


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY")
        sys.exit(1)

    task = TASK_NAVIGATE
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create-table":
            task = TASK_CREATE_TABLE
        elif sys.argv[1] == "--export-dat":
            task = TASK_EXPORT_DAT
        elif sys.argv[1] == "--custom":
            task = " ".join(sys.argv[2:])
        elif sys.argv[1] == "--screenshot":
            # Just take a screenshot and exit
            controller = SSHController()
            path = str(RESULTS_DIR / f"screenshot_{datetime.now().strftime('%H%M%S')}.png")
            png = controller.screenshot(path)
            print(f"Screenshot saved: {path} ({len(png)} bytes)")
            return
        elif sys.argv[1] == "--help":
            print("Usage: python computer_use_ssh.py [OPTIONS]")
            print()
            print("Options:")
            print("  (none)            Navigate to Sage admin console")
            print("  --create-table    Create CF_Equipos table")
            print("  --export-dat      Export CF_ objects as .dat")
            print("  --custom TEXT     Run custom task")
            print("  --screenshot      Take a single screenshot")
            print()
            print(f"  SAGE_VM_IP = {SAGE_VM_IP}")
            return

    # Verify SSH connectivity
    print(f"Checking SSH to {SAGE_VM_IP}...")
    result = ssh_cmd("hostname")
    if "sage-vm" not in result:
        print(f"SSH failed: {result}")
        sys.exit(1)
    print(f"  Connected to {result.strip()}")

    # Verify VMware Player is running
    result = ssh_cmd('tasklist /FI "IMAGENAME eq vmplayer*" /NH')
    if "vmplayer" not in result.lower():
        print("VMware Player not running. Starting it...")
        ssh_cmd('schtasks /run /tn StartSageVM')
        time.sleep(30)

    controller = SSHController()
    run_computer_use_loop(controller, task)


if __name__ == "__main__":
    main()
