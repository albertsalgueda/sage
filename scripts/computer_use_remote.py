#!/usr/bin/env python3
"""
Computer-Use for Sage 200 — runs entirely on sage-kvm.
Uses vncdo CLI for input + QEMU monitor for screenshots.

Upload to sage-kvm and run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 /tmp/computer_use_remote.py
"""

import anthropic
import base64
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
MODEL = "claude-haiku-4-5-20251001"
MAX_STEPS = 30
RESULTS_DIR = Path("/tmp/sage_experiment")
RESULTS_DIR.mkdir(exist_ok=True)
VNCDO = os.path.expanduser("~/.local/bin/vncdo")
VNC_ADDR = "localhost::5900"


# ─── QEMU screenshot ────────────────────────────────────────────────────────

def qemu_screendump(path):
    """Take screenshot via QEMU monitor."""
    ppm = path.replace(".png", ".ppm")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect(("localhost", 4322))
    try: s.recv(4096)
    except: pass
    time.sleep(0.05)
    s.sendall(f"screendump {ppm}\n".encode())
    time.sleep(0.3)
    try: s.recv(4096)
    except: pass
    s.close()
    time.sleep(0.3)
    subprocess.run(["sudo", "chmod", "644", ppm], capture_output=True)
    from PIL import Image
    img = Image.open(ppm)
    img.save(path)
    os.remove(ppm)
    return img.size


# ─── VNC input via vncdo CLI ────────────────────────────────────────────────

def vnc_click(x, y):
    subprocess.run([VNCDO, "-s", VNC_ADDR, "move", str(x), str(y), "click", "1"],
                   capture_output=True, timeout=10)

def vnc_double_click(x, y):
    subprocess.run([VNCDO, "-s", VNC_ADDR, "move", str(x), str(y), "click", "1",
                    "pause", "0.15", "click", "1"],
                   capture_output=True, timeout=10)

def vnc_right_click(x, y):
    subprocess.run([VNCDO, "-s", VNC_ADDR, "move", str(x), str(y), "click", "3"],
                   capture_output=True, timeout=10)

def vnc_type(text):
    subprocess.run([VNCDO, "-s", VNC_ADDR, "type", text],
                   capture_output=True, timeout=30)

def vnc_key(key_name):
    """Press key. Handles Anthropic key names."""
    key_map = {
        "Return": "enter", "Tab": "tab", "Escape": "escape",
        "BackSpace": "backspace", "Delete": "delete",
        "space": "space", "Up": "up", "Down": "down",
        "Left": "left", "Right": "right",
        "Home": "home", "End": "end",
        "Page_Up": "pageup", "Page_Down": "pagedown",
        "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
        "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
        "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
        "Super_L": "super_l", "Control_L": "ctrl_l", "Alt_L": "alt_l",
    }
    # Handle combos like "alt+F4" or "ctrl+Escape"
    if "+" in key_name:
        parts = key_name.split("+")
        # vncdo key format: "key alt-f4" uses dash
        mapped = []
        for p in parts:
            m = key_map.get(p, p.lower())
            mapped.append(m)
        combo = "-".join(mapped)
        subprocess.run([VNCDO, "-s", VNC_ADDR, "key", combo],
                       capture_output=True, timeout=10)
    else:
        k = key_map.get(key_name, key_name.lower())
        subprocess.run([VNCDO, "-s", VNC_ADDR, "key", k],
                       capture_output=True, timeout=10)

def vnc_move(x, y):
    subprocess.run([VNCDO, "-s", VNC_ADDR, "move", str(x), str(y)],
                   capture_output=True, timeout=10)

def vnc_drag(sx, sy, ex, ey):
    # vncdo doesn't have drag, simulate with move + mousedown/up
    subprocess.run([VNCDO, "-s", VNC_ADDR, "move", str(sx), str(sy),
                    "mousedown", "1", "move", str(ex), str(ey), "mouseup", "1"],
                   capture_output=True, timeout=10)


# ─── Execute action ─────────────────────────────────────────────────────────

def execute_action(action):
    """Execute a computer-use action."""
    act = action.get("action", action.get("type"))
    coord = action.get("coordinate")
    text = action.get("text", "")

    if act == "left_click" and coord:
        vnc_click(coord[0], coord[1])
    elif act == "right_click" and coord:
        vnc_right_click(coord[0], coord[1])
    elif act == "double_click" and coord:
        vnc_double_click(coord[0], coord[1])
    elif act == "mouse_move" and coord:
        vnc_move(coord[0], coord[1])
    elif act == "left_click_drag":
        start = action.get("start_coordinate", [0, 0])
        end = coord or [0, 0]
        vnc_drag(start[0], start[1], end[0], end[1])
    elif act == "type" and text:
        vnc_type(text)
    elif act == "key" and text:
        vnc_key(text)
    elif act == "scroll" and coord:
        # Scroll: move to position, then use scroll keys
        vnc_move(coord[0], coord[1])
        direction = action.get("direction", "down")
        for _ in range(3):
            if direction == "up":
                vnc_key("scrollup")
            else:
                vnc_key("scrolldown")
    elif act == "screenshot":
        pass  # handled by loop
    elif act == "wait":
        time.sleep(2)
    else:
        print(f"  ? Unknown action: {act}")


# ─── Main loop ──────────────────────────────────────────────────────────────

def run(task):
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": [{"type": "text", "text": task}]}]
    log = []
    last_tool_id = None
    step = 0
    response = None

    while step < MAX_STEPS:
        step += 1
        ts = datetime.now().strftime("%H%M%S")
        png_path = str(RESULTS_DIR / f"step_{step:03d}.png")

        # Screenshot
        print(f"\n--- Step {step}/{MAX_STEPS} ---")
        try:
            size = qemu_screendump(png_path)
            with open(png_path, "rb") as f:
                b64 = base64.standard_b64encode(f.read()).decode()
            print(f"  Screenshot: {size}")
        except Exception as e:
            print(f"  Screenshot FAILED: {e}")
            break

        # Build message
        img_block = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}
        if step > 1 and last_tool_id:
            messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": last_tool_id, "content": [img_block]}]})
        else:
            messages[0]["content"].append(img_block)

        # Ask Claude
        print("  Asking Claude...")
        try:
            response = client.beta.messages.create(
                model=MODEL, max_tokens=4096,
                tools=[{"type": "computer_20250124", "name": "computer",
                        "display_width_px": SCREEN_WIDTH, "display_height_px": SCREEN_HEIGHT, "display_number": 0}],
                messages=messages, betas=["computer-use-2025-01-24"],
            )
        except Exception as e:
            print(f"  API error: {e}")
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for b in response.content:
                if hasattr(b, "text"): print(f"  Claude: {b.text}")
            print("\n  DONE.")
            break

        # Execute actions
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"  {block.text[:200]}")
            if block.type == "tool_use":
                last_tool_id = block.id
                action = block.input
                act = action.get("action", "?")
                coord = action.get("coordinate", "")
                txt = action.get("text", "")[:30]
                print(f"  >> {act}", end="")
                if coord: print(f" @ {coord}", end="")
                if txt: print(f" '{txt}'", end="")
                print()
                log.append({"step": step, "action": act, "details": action})
                try:
                    execute_action(action)
                    time.sleep(0.8)
                except Exception as e:
                    print(f"  Action failed: {e}")

    # Save log
    log_path = RESULTS_DIR / "log.json"
    with open(log_path, "w") as f:
        json.dump({"task": task, "model": MODEL, "steps": log, "total": step}, f, indent=2)
    print(f"\nLog: {log_path}")
    print(f"Screenshots: {RESULTS_DIR}/step_*.png")


# ─── Task ────────────────────────────────────────────────────────────────────

TASK = """
You are controlling a Windows Server 2019 desktop via remote display.
The display is 1024x768. The interface is in Spanish.

Your task:
1. Look at the current screen and describe what you see.
2. Close the Server Manager window (click X button at top-right, or use Alt+F4)
3. Find and open the Sage 200 application - look for "Sage 200c" icon on the desktop
4. Double-click the Sage 200c icon to open it
5. Once Sage 200 opens, describe what you see

Important tips:
- The Server Manager close button (X) is at approximately the top-right corner of its window
- Desktop icons are on the left side
- The taskbar is at the bottom
- After clicking, wait for the UI to respond before taking the next action
- If an action doesn't seem to work, try a slightly different position
"""

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY"); sys.exit(1)
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else TASK
    run(task)
