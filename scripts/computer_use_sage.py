"""
Computer-Use script for controlling Sage 200 — HEADLESS (no RDP client needed).

Uses VNC to connect programmatically to the Windows server, captures screenshots,
sends keyboard/mouse events, and loops with Anthropic's computer-use API.

Architecture:
    Python script → VNC protocol → GCP Windows Server → VMware → Sage 200 VM

    The script connects directly to VNC on the server. No Microsoft Remote Desktop,
    no local GUI, no macOS screencapture — everything is over the network.

Requirements:
    pip install anthropic vncdotool Pillow

Usage:
    export ANTHROPIC_API_KEY=your_key
    python computer_use_sage.py                    # Navigate Sage admin console
    python computer_use_sage.py --create-table     # Create CF_Equipos table
    python computer_use_sage.py --custom "Your task description here"

    # Override VM IP:
    export SAGE_VM_IP=34.175.136.176
"""

import anthropic
import base64
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

SAGE_VM_IP = os.environ.get("SAGE_VM_IP", "34.175.136.176")
VNC_PORT = int(os.environ.get("VNC_PORT", "5900"))
VNC_PASSWORD = os.environ.get("VNC_PASSWORD", "sage2026")

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-6-20250514"


# ─── VNC Connection ─────────────────────────────────────────────────────────

class VNCController:
    """Headless VNC controller — captures screenshots and sends input over the network."""

    def __init__(self, host: str, port: int = 5900, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self.client = None

    def connect(self):
        """Connect to VNC server."""
        try:
            from vncdotool import api as vnc_api
            self.client = vnc_api.connect(
                f"{self.host}::{self.port}",
                password=self.password
            )
            print(f"✓ Connected to VNC at {self.host}:{self.port}")
            return True
        except ImportError:
            print("vncdotool not available, falling back to RDP screenshot method")
            return False
        except Exception as e:
            print(f"✗ VNC connection failed: {e}")
            return False

    def screenshot(self, save_path: str = None) -> bytes:
        """Capture screenshot via VNC, return as PNG bytes."""
        if self.client:
            self.client.refreshScreen()
            img = self.client.screen
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(png_bytes)
            return png_bytes
        raise RuntimeError("Not connected to VNC")

    def click(self, x: int, y: int, button: int = 1):
        """Click at coordinates. button: 1=left, 2=middle, 3=right."""
        if self.client:
            self.client.mouseMove(x, y)
            time.sleep(0.05)
            self.client.mousePress(button)

    def double_click(self, x: int, y: int):
        """Double-click at coordinates."""
        if self.client:
            self.client.mouseMove(x, y)
            time.sleep(0.05)
            self.client.mousePress(1)
            time.sleep(0.1)
            self.client.mousePress(1)

    def right_click(self, x: int, y: int):
        """Right-click at coordinates."""
        self.click(x, y, button=3)

    def move(self, x: int, y: int):
        """Move mouse to coordinates."""
        if self.client:
            self.client.mouseMove(x, y)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Drag from start to end coordinates."""
        if self.client:
            self.client.mouseMove(start_x, start_y)
            time.sleep(0.05)
            self.client.mouseDown(1)
            time.sleep(0.1)
            self.client.mouseMove(end_x, end_y)
            time.sleep(0.05)
            self.client.mouseUp(1)

    def type_text(self, text: str):
        """Type text string."""
        if self.client:
            self.client.type(text)

    def press_key(self, key: str):
        """Press a key. Maps Anthropic key names to VNC key names."""
        if not self.client:
            return

        # Map Anthropic computer-use key names to VNC key names
        key_map = {
            "Return": "enter",
            "Tab": "tab",
            "Escape": "esc",
            "BackSpace": "bsp",
            "Delete": "del",
            "space": "space",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Home": "home",
            "End": "end",
            "Page_Up": "pgup",
            "Page_Down": "pgdn",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
            "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
            "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
            "Control_L": "ctrl", "Alt_L": "alt", "Shift_L": "shift",
            "Super_L": "super",
        }
        mapped = key_map.get(key, key.lower())
        self.client.keyPress(mapped)

    def scroll(self, x: int, y: int, direction: str, amount: int = 3):
        """Scroll at coordinates. direction: up/down/left/right."""
        if self.client:
            self.client.mouseMove(x, y)
            # VNC scroll: button 4 = up, button 5 = down
            button = 4 if direction == "up" else 5
            for _ in range(amount):
                self.client.mousePress(button)
                time.sleep(0.05)

    def disconnect(self):
        """Disconnect from VNC."""
        if self.client:
            self.client.disconnect()
            print("Disconnected from VNC")


# ─── Fallback: SSH-based screenshot (no VNC needed) ─────────────────────────

class SSHScreenshotController:
    """
    Alternative: Use SSH + PowerShell to take screenshots on the server,
    then download them. No VNC needed, but can't send mouse/keyboard.
    Useful for verification only.
    """

    def __init__(self, host: str, user: str = "albert", key_path: str = None):
        self.host = host
        self.user = user
        self.key_path = key_path

    def screenshot(self, save_path: str) -> bytes:
        """Take screenshot via SSH + PowerShell."""
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, username=self.user, key_filename=self.key_path)

        ps_cmd = '''
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
        $bitmap.Save("C:\\screenshot.png")
        $graphics.Dispose()
        $bitmap.Dispose()
        [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\\screenshot.png"))
        '''

        stdin, stdout, stderr = ssh.exec_command(f'powershell -Command "{ps_cmd}"')
        b64_data = stdout.read().decode().strip()
        ssh.close()

        if b64_data:
            png_bytes = base64.b64decode(b64_data)
            with open(save_path, "wb") as f:
                f.write(png_bytes)
            return png_bytes
        raise RuntimeError(f"Screenshot failed: {stderr.read().decode()}")


# ─── Fallback: FreeRDP-based controller ──────────────────────────────────────

class FreeRDPController:
    """
    Use xfreerdp to maintain a headless RDP session.
    Captures screenshots via /rfx and sends input via xdotool on an Xvfb display.
    Requires: xfreerdp, Xvfb, xdotool (Linux only).
    """

    def __init__(self, host: str, user: str, password: str,
                 width: int = 1920, height: int = 1080):
        self.host = host
        self.user = user
        self.password = password
        self.width = width
        self.height = height
        self.display = ":99"
        self.process = None

    def connect(self):
        """Start Xvfb + xfreerdp in background."""
        import subprocess

        # Start virtual display
        subprocess.Popen([
            "Xvfb", self.display, "-screen", "0",
            f"{self.width}x{self.height}x24"
        ])
        time.sleep(1)

        # Start xfreerdp
        self.process = subprocess.Popen([
            "xfreerdp",
            f"/v:{self.host}",
            f"/u:{self.user}",
            f"/p:{self.password}",
            f"/size:{self.width}x{self.height}",
            "/cert:ignore",
            "+clipboard",
        ], env={**os.environ, "DISPLAY": self.display})
        time.sleep(3)
        print(f"✓ FreeRDP connected to {self.host}")

    def screenshot(self, save_path: str) -> bytes:
        """Capture screenshot via xdotool/import."""
        import subprocess
        subprocess.run([
            "import", "-window", "root", "-display", self.display, save_path
        ], check=True)
        with open(save_path, "rb") as f:
            return f.read()

    def click(self, x: int, y: int, button: int = 1):
        import subprocess
        subprocess.run([
            "xdotool", "mousemove", "--screen", "0", str(x), str(y),
            "click", str(button)
        ], env={**os.environ, "DISPLAY": self.display})

    def type_text(self, text: str):
        import subprocess
        subprocess.run([
            "xdotool", "type", "--delay", "50", text
        ], env={**os.environ, "DISPLAY": self.display})

    def press_key(self, key: str):
        import subprocess
        key_map = {
            "Return": "Return", "Tab": "Tab", "Escape": "Escape",
            "BackSpace": "BackSpace", "space": "space",
            "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
        }
        mapped = key_map.get(key, key)
        subprocess.run([
            "xdotool", "key", mapped
        ], env={**os.environ, "DISPLAY": self.display})


# ─── Computer-Use Loop ──────────────────────────────────────────────────────

def execute_action(controller, action: dict):
    """Execute a computer-use action using the active controller."""
    action_type = action.get("action", action.get("type", "unknown"))

    if action_type == "screenshot":
        return  # Handled by the loop

    elif action_type == "left_click":
        x, y = action["coordinate"]
        controller.click(x, y, button=1)

    elif action_type == "right_click":
        x, y = action["coordinate"]
        controller.right_click(x, y)

    elif action_type == "double_click":
        x, y = action["coordinate"]
        controller.double_click(x, y)

    elif action_type == "mouse_move":
        x, y = action["coordinate"]
        controller.move(x, y)

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


def run_computer_use_loop(controller, task: str, max_steps: int = 50):
    """
    The main computer-use loop:
      1. Take screenshot via VNC/RDP
      2. Send to Claude with computer-use tool
      3. Claude returns action (click, type, etc.)
      4. Execute action via VNC/RDP
      5. Repeat until Claude says done or max_steps reached

    Everything is headless — no local GUI needed.
    """
    client = anthropic.Anthropic()
    log_entries = []
    step = 0

    print(f"\n{'='*60}")
    print(f"  Computer-Use Task")
    print(f"{'='*60}")
    print(f"  {task[:200]}...")
    print(f"{'='*60}\n")

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": task}]
        }
    ]

    last_tool_use_id = None

    while step < max_steps:
        step += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(RESULTS_DIR / f"step_{step:03d}_{timestamp}.png")

        # 1. Take screenshot
        print(f"\n--- Step {step}/{max_steps} ---")
        print("📸 Taking screenshot...")
        try:
            png_bytes = controller.screenshot(screenshot_path)
            screenshot_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            print(f"   Saved: {screenshot_path}")
        except Exception as e:
            print(f"   ✗ Screenshot failed: {e}")
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
        print("🤖 Asking Claude to analyze...")
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
            print(f"   ✗ API error: {e}")
            log_entries.append({
                "step": step, "timestamp": timestamp,
                "action": "api_error", "error": str(e),
                "screenshot": screenshot_path,
            })
            break

        # 4. Process response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Check if Claude is done
        if response.stop_reason == "end_turn":
            for block in assistant_content:
                if hasattr(block, "text"):
                    print(f"\n💬 Claude: {block.text}")
            print("\n✓ Task completed.")
            log_entries.append({
                "step": step, "timestamp": timestamp,
                "action": "end_turn", "screenshot": screenshot_path,
            })
            break

        # 5. Execute tool-use actions
        for block in assistant_content:
            if hasattr(block, "text") and block.text:
                print(f"   💬 {block.text}")

            if block.type == "tool_use":
                last_tool_use_id = block.id
                action = block.input
                action_type = action.get("action", action.get("type", "?"))

                # Log
                coord = action.get("coordinate", "")
                text = action.get("text", "")[:40]
                print(f"   🎯 {action_type}", end="")
                if coord: print(f" @ {coord}", end="")
                if text: print(f" '{text}'", end="")
                print()

                log_entries.append({
                    "step": step, "timestamp": timestamp,
                    "action": action_type,
                    "details": {k: v for k, v in action.items()
                               if k not in ("type", "action")},
                    "screenshot": screenshot_path,
                })

                # Execute
                if action_type != "screenshot":
                    try:
                        execute_action(controller, action)
                        time.sleep(0.5)  # Wait for UI to update
                    except Exception as e:
                        print(f"   ✗ Action failed: {e}")

    # Save log
    log_path = RESULTS_DIR / f"computer_use_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w") as f:
        json.dump({
            "task": task,
            "vm_ip": SAGE_VM_IP,
            "model": MODEL,
            "steps": log_entries,
            "total_steps": step,
            "completed": response.stop_reason == "end_turn" if 'response' in dir() else False,
        }, f, indent=2)

    print(f"\n📋 Log saved: {log_path}")
    return log_entries


# ─── Test Tasks ──────────────────────────────────────────────────────────────

TASK_NAVIGATE_ADMIN = """
You are controlling a Windows desktop that has Sage 200 installed.
The interface is in Spanish.

Your task:
1. Look at the current screen. Describe what you see.
2. Find and open the Sage 200 application (check desktop icons, taskbar, or Start menu)
3. Navigate to: Consola de Administración → Herramientas → Importar Objetos de Repositorio
4. Once you reach the import screen, describe what you see.

Take your time. At each step, describe what you see before taking action.
If you're unsure, take a screenshot first.
"""

TASK_CREATE_TABLE = """
You are controlling a Windows desktop with Sage 200's development environment.
The interface is in Spanish.

Your task is to create a new table in Sage 200:

Table: CF_Equipos
Fields:
  - CodigoEquipo (Character, 5 chars, Primary Key)
  - Nombre (Character, 50 chars)
  - JuegaEuropa (Boolean / Lógico)
  - Competicion (Character, 30 chars)

Steps:
1. Open Sage 200 if not already open
2. Go to the development/customization area (Consola de Administración)
3. Find where to create/modify tables (Herramientas → Tablas or similar)
4. Create the table CF_Equipos with all fields above
5. Save and confirm the table was created

Describe what you see and do at each step. The interface is in Spanish.
"""


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    # Parse task
    task = TASK_NAVIGATE_ADMIN
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create-table":
            task = TASK_CREATE_TABLE
        elif sys.argv[1] == "--custom":
            task = " ".join(sys.argv[2:])
        elif sys.argv[1] == "--help":
            print("Usage: python computer_use_sage.py [OPTIONS]")
            print()
            print("Options:")
            print("  (none)            Navigate to Sage admin console")
            print("  --create-table    Create CF_Equipos table")
            print("  --custom TEXT     Run custom task")
            print()
            print("Environment:")
            print(f"  SAGE_VM_IP     = {SAGE_VM_IP}")
            print(f"  VNC_PORT       = {VNC_PORT}")
            print(f"  VNC_PASSWORD   = {'*' * len(VNC_PASSWORD)}")
            print(f"  ANTHROPIC_API_KEY = {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET'}")
            sys.exit(0)

    # Try VNC first, then FreeRDP, then SSH-only
    print(f"\nConnecting to {SAGE_VM_IP}...")
    controller = VNCController(SAGE_VM_IP, VNC_PORT, VNC_PASSWORD)

    if not controller.connect():
        print("\n⚠ VNC not available.")
        print("  Options:")
        print("  1. Install TightVNC on the server (port 5900)")
        print("  2. Use FreeRDP on Linux: pip install ... (see FreeRDPController)")
        print("  3. SSH screenshot-only mode (can view but not interact)")
        print()
        print("  To install VNC on the server, SSH in and run:")
        print("  choco install tightvnc -y --params '/SET_PASSWORD=sage2026'")
        sys.exit(1)

    try:
        run_computer_use_loop(controller, task)
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()
