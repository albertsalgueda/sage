"""
Computer-Use + Adaptive Thinking validation for Sage 200 VM.

Uses Claude Opus 4.6 with adaptive thinking to analyze and interact
with the Sage 200 VM via VNC.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python test_computer_use_thinking.py
    python test_computer_use_thinking.py --custom "Your task description"
"""

import anthropic
import base64
import io
from PIL import Image, ImageDraw
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

SAGE_VM_IP = os.environ.get("SAGE_VM_IP", "34.175.32.149")
VNC_PORT = int(os.environ.get("VNC_PORT", "5900"))
VNC_PASSWORD = os.environ.get("VNC_PASSWORD", "sage2026")

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

RESULTS_DIR = Path(__file__).parent.parent / "results" / "thinking_test"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "claude-opus-4-6"
MAX_STEPS = 50


# ─── VNC Connection ─────────────────────────────────────────────────────────

class VNCController:
    def __init__(self, host, port=5900, password=""):
        self.host = host
        self.port = port
        self.password = password
        self.client = None

    def connect(self):
        try:
            from vncdotool import api as vnc_api
            self.client = vnc_api.connect(
                f"{self.host}::{self.port}",
                password=self.password
            )
            self.client.timeout = 30
            print(f"  Connected to VNC at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"  VNC connection failed: {e}")
            return False

    def screenshot(self, save_path=None):
        if self.client:
            self.client.refreshScreen()
            img = self.client.screen
            # Save full PNG for GIF generation
            if save_path:
                img.save(save_path, format="PNG")
            # Return compressed JPEG for API (much smaller than PNG)
            img_resized = img.resize((1366, 768), Image.LANCZOS)
            buf = io.BytesIO()
            img_resized.save(buf, format="JPEG", quality=75)
            return buf.getvalue()
        raise RuntimeError("Not connected to VNC")

    def click(self, x, y, button=1):
        if self.client:
            self.client.mouseMove(x, y)
            time.sleep(0.05)
            self.client.mousePress(button)

    def double_click(self, x, y):
        if self.client:
            self.client.mouseMove(x, y)
            time.sleep(0.05)
            self.client.mousePress(1)
            time.sleep(0.1)
            self.client.mousePress(1)

    def right_click(self, x, y):
        self.click(x, y, button=3)

    def move(self, x, y):
        if self.client:
            self.client.mouseMove(x, y)

    def drag(self, sx, sy, ex, ey):
        if self.client:
            self.client.mouseMove(sx, sy)
            time.sleep(0.05)
            self.client.mouseDown(1)
            time.sleep(0.1)
            self.client.mouseMove(ex, ey)
            time.sleep(0.05)
            self.client.mouseUp(1)

    def type_text(self, text):
        """Type text via subprocess vncdotool CLI (avoids blocking API hangs)."""
        self._vnc_cmd(["type", text])

    def press_key(self, key):
        """Press a key or key combination via subprocess vncdotool CLI.

        Anthropic computer-use sends: "Return", "Escape", "alt+F4", "super+d"
        vncdotool CLI expects: "enter", "esc", "alt-f4", "super-d"
        """
        key_map = {
            "Return": "enter", "Tab": "tab", "Escape": "esc",
            "BackSpace": "bsp", "Delete": "del", "space": "space",
            "Up": "up", "Down": "down", "Left": "left", "Right": "right",
            "Home": "home", "End": "end", "Page_Up": "pgup", "Page_Down": "pgdn",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
            "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
            "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
            "Control_L": "ctrl", "Alt_L": "alt", "Shift_L": "shift",
            "Super_L": "super", "super": "super",
            "alt": "alt", "ctrl": "ctrl", "shift": "shift",
        }

        # Convert "alt+F4" → "alt-f4", "super+d" → "super-d"
        if "+" in key:
            parts = key.split("+")
            mapped_parts = []
            for part in parts:
                part = part.strip()
                mapped = key_map.get(part, key_map.get(part.lower(), part.lower()))
                mapped_parts.append(mapped)
            vnc_key = "-".join(mapped_parts)
        else:
            vnc_key = key_map.get(key, key_map.get(key.lower(), key.lower()))

        self._vnc_cmd(["key", vnc_key])

    def _vnc_cmd(self, action_args, timeout=8):
        """Execute vncdotool action via subprocess CLI (avoids blocking API hangs)."""
        venv_bin = os.path.dirname(sys.executable)
        vncdotool_bin = os.path.join(venv_bin, "vncdotool")
        if not os.path.exists(vncdotool_bin):
            vncdotool_bin = "vncdotool"
        cmd = [
            vncdotool_bin,
            "-s", f"{self.host}::{self.port}",
            "-p", self.password,
        ] + action_args
        try:
            result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"    vncdotool stderr: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"    vncdotool timed out after {timeout}s")
        except Exception as e:
            print(f"    vncdotool error: {e}")

    def scroll(self, x, y, direction, amount=3):
        if self.client:
            self.client.mouseMove(x, y)
            button = 4 if direction == "up" else 5
            for _ in range(amount):
                self.client.mousePress(button)
                time.sleep(0.05)

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            print("  Disconnected from VNC")


# ─── Action Execution ──────────────────────────────────────────────────────

def execute_action(controller, action):
    action_type = action.get("action", action.get("type", "unknown"))

    if action_type == "screenshot":
        return
    elif action_type == "left_click":
        controller.click(*action["coordinate"], button=1)
    elif action_type == "right_click":
        controller.right_click(*action["coordinate"])
    elif action_type == "double_click":
        controller.double_click(*action["coordinate"])
    elif action_type == "mouse_move":
        controller.move(*action["coordinate"])
    elif action_type == "left_click_drag":
        controller.drag(*action["start_coordinate"], *action["coordinate"])
    elif action_type == "type":
        controller.type_text(action["text"])
    elif action_type == "key":
        # computer_20251124 uses "text" field for key name, not "key"
        key_value = action.get("key", action.get("text", ""))
        if key_value:
            controller.press_key(key_value)
    elif action_type == "scroll":
        x, y = action["coordinate"]
        controller.scroll(x, y, action.get("scroll_direction", "down"), action.get("scroll_amount", 3))
    else:
        print(f"    Unknown action: {action_type}")


# ─── Main Computer-Use Loop ───────────────────────────────────────────────

def run_test(controller, task):
    client = anthropic.Anthropic()
    log_entries = []
    last_tool_use_id = None
    step = 0

    print(f"\n{'='*70}")
    print(f"  COMPUTER-USE + ADAPTIVE THINKING")
    print(f"  Model: {MODEL} | VM: {SAGE_VM_IP} | Thinking: adaptive")
    print(f"{'='*70}\n")

    messages = [{"role": "user", "content": [{"type": "text", "text": task}]}]

    while step < MAX_STEPS:
        step += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(RESULTS_DIR / f"step_{step:03d}_{timestamp}.png")

        print(f"\n--- Step {step}/{MAX_STEPS} ---")
        print("  Taking screenshot...")
        try:
            png_bytes = controller.screenshot(screenshot_path)
            screenshot_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            print(f"  Saved: {screenshot_path} ({len(png_bytes)} bytes)")
        except Exception as e:
            print(f"  Screenshot failed: {e}")
            break

        if step > 1 and last_tool_use_id:
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": last_tool_use_id,
                    "content": [{
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": screenshot_b64}
                    }]
                }]
            })
        else:
            messages[0]["content"].append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": screenshot_b64}
            })

        # Sliding window: keep system message + last 20 messages to avoid 413
        MAX_CONTEXT_MSGS = 20
        if len(messages) > MAX_CONTEXT_MSGS + 1:
            messages = [messages[0]] + messages[-(MAX_CONTEXT_MSGS):]

        print("  Calling Claude Opus 4.6...")
        try:
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                betas=["computer-use-2025-11-24"],
                tools=[{
                    "type": "computer_20251124",
                    "name": "computer",
                    "display_width_px": SCREEN_WIDTH,
                    "display_height_px": SCREEN_HEIGHT,
                    "display_number": 0,
                }],
                messages=messages,
            )
        except Exception as e:
            print(f"  API error: {e}")
            log_entries.append({"step": step, "error": str(e)})
            break

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        thinking_text = ""
        response_text = ""

        for block in assistant_content:
            if hasattr(block, "type"):
                if block.type == "thinking":
                    thinking_text = block.thinking
                    preview = thinking_text[:300]
                    if len(thinking_text) > 300:
                        preview += f"... [{len(thinking_text)} chars]"
                    print(f"\n  [THINKING] {preview}")

                elif block.type == "text":
                    response_text = block.text
                    print(f"\n  [RESPONSE] {block.text}")

                elif block.type == "tool_use":
                    last_tool_use_id = block.id
                    action = block.input
                    action_type = action.get("action", "?")
                    coord = action.get("coordinate", "")
                    text = action.get("text", "")[:40]
                    key = action.get("key", "")
                    print(f"  [ACTION] {action_type}", end="")
                    if coord: print(f" @ {coord}", end="")
                    if text: print(f" '{text}'", end="")
                    if key: print(f" key='{key}'", end="")
                    print()

                    log_entries.append({
                        "step": step, "timestamp": timestamp,
                        "thinking_length": len(thinking_text),
                        "thinking_preview": thinking_text[:200],
                        "response_text": response_text[:200],
                        "action": action_type,
                        "action_details": {k: v for k, v in action.items() if k not in ("type", "action")},
                        "screenshot": screenshot_path,
                    })

                    if action_type != "screenshot":
                        try:
                            execute_action(controller, action)
                            time.sleep(0.8)
                        except Exception as e:
                            print(f"    Action failed: {e}")

        if response.stop_reason == "end_turn":
            print(f"\n  Task completed (stop_reason=end_turn)")
            log_entries.append({
                "step": step, "timestamp": timestamp,
                "action": "end_turn",
                "response_text": response_text[:500],
                "screenshot": screenshot_path,
            })
            break

        usage = response.usage
        print(f"  [USAGE] in={usage.input_tokens} out={usage.output_tokens}")

    # Save results
    results = {
        "test": "computer_use_adaptive_thinking",
        "model": MODEL, "vm_ip": SAGE_VM_IP,
        "thinking": "adaptive",
        "timestamp": datetime.now().isoformat(),
        "total_steps": step,
        "completed": response.stop_reason == "end_turn" if 'response' in dir() else False,
        "steps": log_entries,
    }
    log_path = RESULTS_DIR / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved: {log_path}")

    gif_path = generate_gif(log_entries)
    return results, gif_path


def generate_gif(log_entries):
    """Generate an animated GIF from session screenshots with overlays."""


    screenshots = []
    actions = []
    for entry in log_entries:
        path = entry.get("screenshot", "")
        if path and os.path.exists(path) and os.path.getsize(path) > 10000:
            screenshots.append(path)
            actions.append({
                "action": entry.get("action", ""),
                "details": entry.get("action_details", {}),
                "text": entry.get("response_text", "")[:80],
            })

    if len(screenshots) < 2:
        print("  Not enough screenshots for GIF")
        return None

    print(f"\n  Generating GIF from {len(screenshots)} frames...")
    frames = []
    for i, (path, action_info) in enumerate(zip(screenshots, actions)):
        img = Image.open(path).convert("RGBA")
        img = img.resize((960, 540), Image.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Step counter
        draw.rectangle([0, 0, 960, 30], fill=(0, 0, 0, 180))
        draw.text((10, 7), f"Step {i+1}/{len(screenshots)}", fill="white")

        # Click indicator
        action = action_info.get("action", "")
        coord = action_info.get("details", {}).get("coordinate", None)
        if coord:
            cx = int(coord[0] * 960 / SCREEN_WIDTH)
            cy = int(coord[1] * 540 / SCREEN_HEIGHT)
            draw.ellipse([cx-12, cy-12, cx+12, cy+12], outline="red", width=3)
            draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill="red")

        # Action label
        if action:
            label = action
            if coord: label += f" @ ({coord[0]}, {coord[1]})"
            key = action_info.get("details", {}).get("key", "")
            if key: label += f" key='{key}'"
            draw.rectangle([0, 510, 960, 540], fill=(0, 0, 0, 180))
            draw.text((10, 517), label, fill=(255, 200, 0))

        # Response text
        text = action_info.get("text", "")
        if text:
            draw.rectangle([0, 30, 960, 50], fill=(0, 60, 120, 160))
            draw.text((10, 33), text[:100], fill="white")

        frames.append(img.convert("RGB"))

    gif_path = RESULTS_DIR / f"sage_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=2500, loop=0)
    size_kb = os.path.getsize(gif_path) / 1024
    print(f"  GIF saved: {gif_path} ({size_kb:.0f} KB)")
    return str(gif_path)


# ─── Task Prompts ────────────────────────────────────────────────────────

TASK_OPEN_SAGE = """You are controlling a Windows Server desktop via VNC at 1920x1080 resolution.
VMware Player is already running with a Sage 200 VM inside it.
The Sage 200 VM is currently at the Windows lock screen showing "Presiona Ctrl+Alt+Supr para desbloquear."

YOUR MISSION: Unlock the VM, log into Windows, and find & open the Sage 200 application.

STEP BY STEP PLAN:

1. WAKE UP: Click center of screen (960, 540) to wake up the display.

2. UNLOCK THE VM: The VM is inside VMware Player. To send Ctrl+Alt+Delete to the VM:
   - Click on the VMware "Player" dropdown menu at the top-left of the VMware window
   - Select "Send Ctrl+Alt+Del" from the dropdown menu
   - This will bring up the Windows login screen inside the VM

3. LOG IN: Try these passwords at the login screen (the username should be pre-filled):
   - First try: Sage2020
   - Then: sage200
   - Then: Sage200
   - Then: 1234
   - Then: admin
   - Then: password
   - Then: Password1
   - Then: Sage200!
   - Then: SageSQL
   - Then: (empty — just press Enter)
   Type the password and press Enter.

4. FIND SAGE 200: Once logged into Windows desktop inside the VM:
   - Look for Sage 200 icons on the desktop (might be named "Consola de Administración" or "Sage 200")
   - If no desktop icons, check the taskbar
   - If nothing visible, use the Windows Start menu inside the VM to search for "Sage"
   - Double-click to open Sage 200

5. DESCRIBE SAGE: Once Sage 200 is open, describe everything you see — menus, windows, options.

IMPORTANT NOTES:
- The outer Windows (host) is in English. The VM inside VMware is in Spanish.
- Click INSIDE the VMware window to interact with the VM.
- When you need to type a password, click on the password field first, then type.
- If a password is wrong, the screen will show an error. Try the next password.
- DO NOT use keyboard shortcuts that won't work — instead use MOUSE CLICKS on menus.
- "Player" menu is at the TOP LEFT of the VMware Player window."""


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    task = TASK_OPEN_SAGE
    if len(sys.argv) > 1:
        if sys.argv[1] == "--custom":
            task = " ".join(sys.argv[2:])
        elif sys.argv[1] == "--help":
            print("Usage: python test_computer_use_thinking.py [--custom TEXT]")
            sys.exit(0)

    print(f"Connecting to VNC at {SAGE_VM_IP}:{VNC_PORT}...")
    controller = VNCController(SAGE_VM_IP, VNC_PORT, VNC_PASSWORD)

    if not controller.connect():
        print("\nVNC connection failed.")
        sys.exit(1)

    try:
        results, gif_path = run_test(controller, task)
        print(f"\n{'='*70}")
        print(f"  TEST SUMMARY")
        print(f"{'='*70}")
        print(f"  Steps executed: {results['total_steps']}")
        print(f"  Completed: {results['completed']}")
        if gif_path:
            print(f"  GIF: {gif_path}")
        print(f"{'='*70}\n")
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()
