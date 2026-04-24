"""
Computer-Use script for Sage 200 via QEMU monitor on sage-kvm.

Uses SSH + QEMU monitor for screenshots (screendump) and QEMU monitor
for keyboard/mouse input. No VNC library needed.

Architecture:
    Python (local) → SSH → sage-kvm → QEMU monitor → Windows VM

Requirements:
    pip install anthropic Pillow

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python computer_use_qemu.py                     # Navigate Sage admin
    python computer_use_qemu.py --create-table      # Create CF_Equipos
    python computer_use_qemu.py --custom "task..."  # Custom task
"""

import anthropic
import base64
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

SAGE_KVM_IP = os.environ.get("SAGE_KVM_IP", "34.175.231.65")
GCP_ZONE = "europe-southwest1-a"
GCP_PROJECT = "illuminator-optimai"
GCP_VM_NAME = "sage-kvm"

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768

RESULTS_DIR = Path(__file__).parent.parent / "results" / "qemu_experiment"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "claude-haiku-4-5-20251001"
MAX_STEPS = 50


# ─── QEMU Controller via SSH ────────────────────────────────────────────────

class QEMUController:
    """Control QEMU VM via monitor commands over SSH."""

    def __init__(self, vm_name, zone, project):
        self.vm_name = vm_name
        self.zone = zone
        self.project = project
        self._step = 0

    def _ssh(self, cmd):
        """Run command on sage-kvm via direct SSH."""
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
             "-i", os.path.expanduser("~/.ssh/google_compute_engine"),
             f"albertsalgueda@{SAGE_KVM_IP}", cmd],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip(), result.stderr.strip()

    def _helper(self, *args):
        """Call the remote qemu_helper.py script."""
        cmd = "python3 /tmp/qemu_helper.py " + " ".join(str(a) for a in args)
        out, err = self._ssh(cmd)
        if out:
            try:
                return json.loads(out.split("\n")[-1])
            except json.JSONDecodeError:
                pass
        return {"ok": False, "error": err or out}

    def _scp_download(self, remote_path, local_path):
        """Download file via SCP."""
        subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no",
             "-i", os.path.expanduser("~/.ssh/google_compute_engine"),
             f"albertsalgueda@{SAGE_KVM_IP}:{remote_path}", local_path],
            capture_output=True, timeout=30
        )

    def screenshot(self, save_path=None):
        """Capture screenshot via remote helper."""
        self._step += 1
        remote_png = f"/tmp/screen_{self._step}.png"

        result = self._helper("screenshot", remote_png)
        if not result.get("ok"):
            raise RuntimeError(f"Screenshot failed: {result}")

        local_path = save_path or str(RESULTS_DIR / f"screen_{self._step:03d}.png")
        self._scp_download(remote_png, local_path)

        with open(local_path, "rb") as f:
            return f.read()

    def click(self, x, y, button=1):
        self._helper("click", x, y, button)

    def double_click(self, x, y):
        self._helper("dblclick", x, y)

    def right_click(self, x, y):
        self._helper("click", x, y, 3)

    def move(self, x, y):
        self._helper("move", x, y)

    def drag(self, start_x, start_y, end_x, end_y):
        self._helper("click", start_x, start_y)

    def type_text(self, text):
        # Escape quotes for shell
        safe = text.replace("'", "'\\''")
        self._helper("type", f"'{safe}'")

    def press_key(self, key):
        self._helper("key", key)

    def disconnect(self):
        """No-op for QEMU controller."""
        pass


# ─── Action Executor ─────────────────────────────────────────────────────────

def execute_action(controller, action):
    """Execute a computer-use action from Claude."""
    action_type = action.get("action", action.get("type"))
    coord = action.get("coordinate")

    if action_type == "left_click" and coord:
        controller.click(coord[0], coord[1])
    elif action_type == "right_click" and coord:
        controller.right_click(coord[0], coord[1])
    elif action_type == "double_click" and coord:
        controller.double_click(coord[0], coord[1])
    elif action_type == "mouse_move" and coord:
        controller.move(coord[0], coord[1])
    elif action_type == "left_click_drag":
        start = action.get("start_coordinate", [0, 0])
        end = coord or [0, 0]
        controller.drag(start[0], start[1], end[0], end[1])
    elif action_type == "type" and action.get("text"):
        controller.type_text(action["text"])
    elif action_type == "key" and action.get("text"):
        controller.press_key(action["text"])
    elif action_type == "scroll":
        # QEMU doesn't have a simple scroll, use mouse_button with wheel
        direction = action.get("coordinate", [0, 0])
        # Button 4 = scroll up, 5 = scroll down in QEMU
        if coord and coord[1] < 0:
            for _ in range(3):
                controller._qemu_cmd("mouse_button 8")  # scroll up
                controller._qemu_cmd("mouse_button 0")
        else:
            for _ in range(3):
                controller._qemu_cmd("mouse_button 16")  # scroll down
                controller._qemu_cmd("mouse_button 0")
    elif action_type == "screenshot":
        pass  # Will take screenshot on next loop
    else:
        print(f"   ⚠ Unknown action: {action_type}")


# ─── Computer-Use Loop ───────────────────────────────────────────────────────

def run_computer_use_loop(controller, task, max_steps=MAX_STEPS):
    """Main loop: screenshot → Claude → action → repeat."""
    client = anthropic.Anthropic()

    messages = [{
        "role": "user",
        "content": [{"type": "text", "text": task}]
    }]

    log_entries = []
    last_tool_use_id = None
    step = 0
    response = None

    while step < max_steps:
        step += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(RESULTS_DIR / f"step_{step:03d}_{timestamp}.png")

        # 1. Take screenshot
        print(f"\n--- Step {step}/{max_steps} ---")
        print("Taking screenshot...")
        try:
            png_bytes = controller.screenshot(screenshot_path)
            screenshot_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            print(f"   Saved: {screenshot_path} ({len(png_bytes)} bytes)")
        except Exception as e:
            print(f"   Screenshot failed: {e}")
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
        print("Asking Claude...")
        try:
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=[{
                    "type": "computer_20250124",
                    "name": "computer",
                    "display_width_px": SCREEN_WIDTH,
                    "display_height_px": SCREEN_HEIGHT,
                    "display_number": 0,
                }],
                messages=messages,
                betas=["computer-use-2025-01-24"],
            )
        except Exception as e:
            print(f"   API error: {e}")
            log_entries.append({"step": step, "action": "api_error", "error": str(e)})
            break

        # 4. Process response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            for block in assistant_content:
                if hasattr(block, "text"):
                    print(f"\n   Claude: {block.text}")
            print("\n   Task completed.")
            log_entries.append({"step": step, "action": "end_turn"})
            break

        # 5. Execute tool-use actions
        for block in assistant_content:
            if hasattr(block, "text") and block.text:
                print(f"   {block.text}")

            if block.type == "tool_use":
                last_tool_use_id = block.id
                action = block.input
                action_type = action.get("action", "?")
                coord = action.get("coordinate", "")
                text = action.get("text", "")[:40]

                print(f"   -> {action_type}", end="")
                if coord: print(f" @ {coord}", end="")
                if text: print(f" '{text}'", end="")
                print()

                log_entries.append({
                    "step": step, "timestamp": timestamp,
                    "action": action_type,
                    "details": {k: v for k, v in action.items() if k != "action"},
                    "screenshot": screenshot_path,
                })

                if action_type != "screenshot":
                    try:
                        execute_action(controller, action)
                        time.sleep(1)  # Wait for UI update
                    except Exception as e:
                        print(f"   Action failed: {e}")

    # Save log
    log_path = RESULTS_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w") as f:
        json.dump({
            "task": task,
            "model": MODEL,
            "vm": GCP_VM_NAME,
            "steps": log_entries,
            "total_steps": step,
        }, f, indent=2)
    print(f"\nLog saved: {log_path}")

    # Generate video from screenshots
    generate_video()

    return log_entries


def generate_video():
    """Assemble screenshots into MP4 video."""
    pngs = sorted(RESULTS_DIR.glob("step_*.png"))
    if len(pngs) < 2:
        print("Not enough screenshots for video")
        return

    video_path = RESULTS_DIR / f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    # Use ffmpeg
    list_file = RESULTS_DIR / "frames.txt"
    with open(list_file, "w") as f:
        for p in pngs:
            f.write(f"file '{p}'\n")
            f.write("duration 1.5\n")
        f.write(f"file '{pngs[-1]}'\n")

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", "scale=1280:960",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(video_path)
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Video: {video_path}")
    else:
        print(f"Video generation failed: {result.stderr[-200:]}")

    list_file.unlink(missing_ok=True)


# ─── Tasks ────────────────────────────────────────────────────────────────────

TASK_NAVIGATE = """
You are controlling a Windows Server 2019 desktop via QEMU.
The display is 1024x768. The interface is in Spanish.

Your task:
1. Look at the current screen and describe what you see.
2. Close any open windows (Server Manager, etc.)
3. Look for the Sage 200 application - check desktop icons, taskbar, or Start menu
4. If you find Sage 200, open it
5. Describe what you see at each step

Take your time. Describe before acting.
"""

TASK_CREATE_TABLE = """
You are controlling a Windows Server 2019 desktop with Sage 200 installed.
The display is 1024x768. The interface is in Spanish.

Your task is to create a new table in Sage 200's development environment:

Table: CF_Equipos
Fields:
  - CodigoEquipo (Character, 5 chars, Primary Key)
  - Nombre (Character, 50 chars)
  - JuegaEuropa (Boolean / Logico)
  - Competicion (Character, 30 chars)

Steps:
1. Open Sage 200 (check desktop, taskbar, Start menu)
2. Navigate to: Consola de Administracion > Herramientas
3. Find where to create tables
4. Create CF_Equipos with all fields
5. Save

Describe what you see at each step.
"""


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY")
        sys.exit(1)

    task = TASK_NAVIGATE
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create-table":
            task = TASK_CREATE_TABLE
        elif sys.argv[1] == "--custom":
            task = " ".join(sys.argv[2:])

    print(f"QEMU VM: {GCP_VM_NAME} ({SAGE_KVM_IP})")
    print(f"Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    print(f"Model: {MODEL}")
    print(f"Results: {RESULTS_DIR}")

    controller = QEMUController(GCP_VM_NAME, GCP_ZONE, GCP_PROJECT)

    # Test screenshot
    print("\nTesting screenshot...")
    try:
        test_png = controller.screenshot(str(RESULTS_DIR / "test_initial.png"))
        print(f"   OK ({len(test_png)} bytes)")
    except Exception as e:
        print(f"   FAILED: {e}")
        sys.exit(1)

    run_computer_use_loop(controller, task)


if __name__ == "__main__":
    main()
