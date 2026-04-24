#!/usr/bin/env python3
"""
Computer-use agent via FreeRDP window on Mac.

Instead of VNC (which shows black), this script:
  1. Captures screenshots of the FreeRDP window using screencapture -l <window_id>
  2. Sends them to Claude Opus with computer_20251124 tool
  3. Translates Claude's click coords (1280x720 space) → Mac logical screen coords
  4. Executes actions via cliclick (mouse) + osascript (keyboard)

The FreeRDP window shows the GCP Windows Server host. Inside it VMware Player
runs the Sage 200 Windows VM. We need to:
  Step 1: Unlock Windows host (Ctrl+Alt+Del → password h[Nk8;ift|FF=^Q)
  Step 2: Navigate VMware Player → click into Sage VM
  Step 3: Try Sage VM passwords (Lortnoc2023+, Lortnoc, admin, 1234)
  Step 4: Open Sage 200 application
  Step 5: Do something in Sage 200 for the demo
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
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-opus-4-5"

# FreeRDP window geometry (Mac logical coords, from System Events)
FREERDP_WIN_X = 224
FREERDP_WIN_Y = 189
FREERDP_WIN_W = 640
FREERDP_WIN_H = 388
MACOS_TITLEBAR_H = 28     # Mac title bar logical px

# FreeRDP connected at 1280×720 inside the window
WINDOWS_W = 1280
WINDOWS_H = 720

# Mac content area (below title bar)
CONTENT_X = FREERDP_WIN_X
CONTENT_Y = FREERDP_WIN_Y + MACOS_TITLEBAR_H   # 217
CONTENT_W = FREERDP_WIN_W                        # 640
CONTENT_H = FREERDP_WIN_H - MACOS_TITLEBAR_H    # 360

# Scale factors: Windows 1280×720 → Mac content 640×360
SCALE_X = CONTENT_W / WINDOWS_W   # 0.5
SCALE_Y = CONTENT_H / WINDOWS_H   # 0.5

RESULTS_DIR = Path(__file__).parent.parent / "results" / "freerdp_agent"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_STEPS = 60

# ── Window ID (refresh each run in case window moved) ─────────────────────────
def get_freerdp_window_id() -> tuple[int, int, int, int, int]:
    """Return (window_id, x, y, w, h) for the sdl-freerdp window."""
    script = """
import CoreGraphics
import Foundation

let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[String: Any]]
for w in windows {
    if let name = w["kCGWindowOwnerName"] as? String, name.contains("sdl") {
        let wid = w["kCGWindowNumber"] as! Int
        let bounds = w["kCGWindowBounds"] as! [String: Any]
        let x = bounds["X"] as! Int
        let y = bounds["Y"] as! Int
        let ww = bounds["Width"] as! Int
        let wh = bounds["Height"] as! Int
        print("\\(wid) \\(x) \\(y) \\(ww) \\(wh)")
        break
    }
}
"""
    r = subprocess.run(["swift", "-"], input=script, capture_output=True, text=True, timeout=10)
    if r.stdout.strip():
        parts = r.stdout.strip().split()
        return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
    return None


def focus_freerdp():
    """Bring FreeRDP window to front."""
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to set frontmost of first process whose name is "sdl-freerdp" to true'
    ], capture_output=True)
    time.sleep(0.3)


def take_screenshot(save_path: str, window_id: int) -> bytes:
    """Capture FreeRDP window, crop title bar, resize to 1280×720 for Claude."""
    tmp = "/tmp/freerdp_raw_cap.png"
    subprocess.run(["screencapture", "-x", "-l", str(window_id), tmp],
                   capture_output=True, check=True)

    img = Image.open(tmp)
    W, H = img.size  # Retina: ~1280×776 (title bar ~56px at 2x)
    # Detect title bar height: assume title bar is ~56px at 2x retina
    # Content aspect should be 16:9 (1280×720), so content_h = W * 720 / 1280
    content_h_expected = int(W * WINDOWS_H / WINDOWS_W)
    titlebar_px = H - content_h_expected

    # Crop title bar
    cropped = img.crop((0, titlebar_px, W, H))  # (left, top, right, bottom)

    # Resize to exactly 1280×720 for consistent Claude coords
    resized = cropped.resize((WINDOWS_W, WINDOWS_H), Image.LANCZOS)

    if save_path:
        resized.save(save_path, "PNG")

    buf = io.BytesIO()
    resized.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def windows_to_mac(wx: int, wy: int, win_x: int, win_y: int) -> tuple[int, int]:
    """Convert 1280×720 Windows coords → Mac logical screen coords."""
    mx = win_x + MACOS_TITLEBAR_H//2 + int(wx * SCALE_X)   # slight padding
    my = win_y + MACOS_TITLEBAR_H + int(wy * SCALE_Y)
    return mx, my


def click(wx: int, wy: int, win_x: int, win_y: int, button: str = "c"):
    """Click at Windows coords. button: c=left, rc=right, dc=double"""
    mx, my = windows_to_mac(wx, wy, win_x, win_y)
    focus_freerdp()
    time.sleep(0.1)
    subprocess.run(["cliclick", f"{button}:{mx},{my}"], capture_output=True)


def mouse_move(wx: int, wy: int, win_x: int, win_y: int):
    mx, my = windows_to_mac(wx, wy, win_x, win_y)
    subprocess.run(["cliclick", f"m:{mx},{my}"], capture_output=True)


def type_text(text: str):
    """Type text into the focused FreeRDP window."""
    focus_freerdp()
    time.sleep(0.2)
    # Use osascript keystroke for safe character delivery
    # Escape special chars for AppleScript string
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run([
        "osascript", "-e",
        f'tell application "System Events" to keystroke "{safe}"'
    ], capture_output=True)


def press_key(key: str):
    """Press a special key or combo. Examples: Return, Tab, escape, ctrl+alt+Delete"""
    focus_freerdp()
    time.sleep(0.1)

    # Map Anthropic computer-use key names to osascript
    key_map = {
        "Return": "return", "return": "return",
        "Enter": "return", "enter": "return",
        "Tab": "tab", "tab": "tab",
        "Escape": "escape", "escape": "escape",
        "Delete": "delete", "BackSpace": "delete",
        "space": "space",
        "ctrl+alt+Delete": "ctrl_alt_del",
        "ctrl+alt+delete": "ctrl_alt_del",
    }

    mapped = key_map.get(key, key.lower())

    if mapped == "ctrl_alt_del":
        # In FreeRDP, Ctrl+Alt+End sends Ctrl+Alt+Delete to the remote
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to key code 119 using {control down, option down}'
        ], capture_output=True)
        return

    # Simple key codes
    key_codes = {
        "return": 36, "tab": 48, "escape": 53, "delete": 51,
        "space": 49, "f1": 122, "f2": 120, "f3": 99, "f4": 118,
        "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f12": 111,
        "up": 126, "down": 125, "left": 123, "right": 124,
        "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    }
    if mapped in key_codes:
        kc = key_codes[mapped]
        subprocess.run([
            "osascript", "-e",
            f'tell application "System Events" to key code {kc}'
        ], capture_output=True)
    else:
        # Try keystroke
        subprocess.run([
            "osascript", "-e",
            f'tell application "System Events" to keystroke "{mapped}"'
        ], capture_output=True)


def execute_action(action: dict, win_x: int, win_y: int):
    """Execute a computer-use tool action."""
    atype = action.get("type", "")

    if atype == "screenshot":
        pass  # handled in loop

    elif atype == "mouse_move":
        x, y = action["coordinate"]
        mouse_move(x, y, win_x, win_y)

    elif atype == "left_click":
        x, y = action["coordinate"]
        click(x, y, win_x, win_y, "c")

    elif atype == "double_click":
        x, y = action["coordinate"]
        click(x, y, win_x, win_y, "dc")

    elif atype == "right_click":
        x, y = action["coordinate"]
        click(x, y, win_x, win_y, "rc")

    elif atype == "left_click_drag":
        sx, sy = action["start_coordinate"]
        ex, ey = action["end_coordinate"]
        smx, smy = windows_to_mac(sx, sy, win_x, win_y)
        emx, emy = windows_to_mac(ex, ey, win_x, win_y)
        focus_freerdp()
        subprocess.run(["cliclick", f"dd:{smx},{smy}", f"du:{emx},{emy}"], capture_output=True)

    elif atype == "type":
        text = action.get("text", "")
        type_text(text)

    elif atype == "key":
        key = action.get("key", "")
        press_key(key)

    elif atype == "scroll":
        x, y = action["coordinate"]
        direction = action.get("direction", "down")
        amount = action.get("amount", 3)
        mx, my = windows_to_mac(x, y, win_x, win_y)
        focus_freerdp()
        for _ in range(amount):
            scroll_dir = "du" if direction == "up" else "dd"
            # osascript scroll
            subprocess.run([
                "osascript", "-e",
                f'tell application "System Events" to scroll (get position of first window of first process whose name is "sdl-freerdp") direction {direction}'
            ], capture_output=True)
            time.sleep(0.1)


# ── Main loop ─────────────────────────────────────────────────────────────────

TASK = """
You are controlling a Windows Server 2022 machine via an RDP window. Your goal is to:

STEP 1: The Windows host is at a LOCK SCREEN (Spanish: "Presiona Ctrl+Alt+Supr para desbloquear").
  - Send Ctrl+Alt+Delete by pressing key "ctrl+alt+Delete"
  - Wait for the login screen to appear
  - Click the password field
  - Type the password: h[Nk8;ift|FF=^Q
  - Press Enter
  - Wait for the Windows desktop to load

STEP 2: Once on the Windows desktop, you should see VMware Workstation Player 17 running with "Sage 200" VM.
  - Click on the VMware Player window to focus it
  - The Sage 200 VM should be at a Windows login screen (user: Administrador)
  - Click inside the VMware window to focus the Sage VM

STEP 3: Unlock the Sage VM (it's a nested Windows Server inside VMware).
  - You may need to click inside VMware first to capture the mouse
  - Try sending Ctrl+Alt+Insert to send Ctrl+Alt+Delete to the guest VM
  - Try passwords in this order: Lortnoc2023+, Lortnoc, admin, 1234
  - After typing each password, press Enter and wait 3-4 seconds to see if it works
  - If a password fails, you'll see a "wrong password" indicator or the screen stays the same

STEP 4: Once logged into the Sage VM:
  - Look for the Sage 200 application icon on the Desktop or Start menu
  - Open Sage 200 (look for "Sage 200" or "Consola de Administración")
  - Wait for it to fully load

STEP 5: Once Sage 200 is open, navigate it briefly to show it working.

IMPORTANT NOTES:
- The screen coordinates are 1280×720
- The Windows host may have VMware Player showing a VM at a login screen
- Be patient: each step may take 5-10 seconds
- If you see a black screen, try clicking around or pressing keys to wake the display
- VMware captures mouse/keyboard — to release: press Ctrl+Alt
- To send Ctrl+Alt+Delete to the GUEST VM (inside VMware): use Ctrl+Alt+Insert
- The Windows taskbar is at the bottom of the 1280×720 screen
"""


def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("=" * 60)
    print("FreeRDP Computer-Use Agent")
    print(f"Task: Unlock Windows host → Sage VM → Open Sage 200")
    print("=" * 60)

    # Get fresh window geometry
    win_info = get_freerdp_window_id()
    if not win_info:
        print("ERROR: FreeRDP window not found! Is sdl-freerdp running?")
        sys.exit(1)

    win_id, win_x, win_y, win_w, win_h = win_info
    print(f"FreeRDP window: ID={win_id}, pos=({win_x},{win_y}), size={win_w}×{win_h}")

    # Update globals with fresh window position
    global CONTENT_X, CONTENT_Y
    CONTENT_X = win_x
    CONTENT_Y = win_y + MACOS_TITLEBAR_H

    # Focus FreeRDP before starting
    focus_freerdp()
    time.sleep(0.5)

    messages = []
    screenshot_paths = []
    step = 0
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        while step < MAX_STEPS:
            step += 1
            print(f"\n─── Step {step}/{MAX_STEPS} ───────────────────────────────")

            # Take screenshot
            shot_path = str(RESULTS_DIR / f"step_{step:03d}_{run_id}.png")
            img_bytes = take_screenshot(shot_path, win_id)
            img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            screenshot_paths.append(shot_path)
            print(f"  Screenshot: {Path(shot_path).name}")

            # Build message
            if not messages:
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": TASK},
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                        },
                        {"type": "text", "text": "This is the current state of the screen. What do you see and what is your first action?"}
                    ]
                }]
            else:
                # Add screenshot as tool result for last tool use
                messages[-1]["content"].append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                })

            # Call Claude
            print("  Calling Claude Opus...")
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=[{
                    "type": "computer_20251124",
                    "name": "computer",
                    "display_width_px": WINDOWS_W,
                    "display_height_px": WINDOWS_H,
                }],
                messages=messages,
                betas=["computer-use-2025-11-24"],
                thinking={"type": "enabled", "budget_tokens": 2000},
            )

            # Parse response
            assistant_content = []
            actions_taken = []
            stop_reason = response.stop_reason

            for block in response.content:
                if block.type == "thinking":
                    print(f"  💭 {block.thinking[:200]}...")
                    assistant_content.append({"type": "thinking", "thinking": block.thinking})

                elif block.type == "text":
                    print(f"  💬 {block.text[:300]}")
                    assistant_content.append({"type": "text", "text": block.text})

                elif block.type == "tool_use" and block.name == "computer":
                    action = block.input
                    action_type = action.get("type", "unknown")
                    print(f"  🖱️  Action: {action_type} {action}")
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": "computer",
                        "input": action
                    })
                    actions_taken.append((block.id, action))

            # Add assistant message
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute actions
            if actions_taken:
                tool_results = []
                for tool_id, action in actions_taken:
                    if action.get("type") == "screenshot":
                        # Take new screenshot
                        shot_path2 = str(RESULTS_DIR / f"step_{step:03d}b_{run_id}.png")
                        new_bytes = take_screenshot(shot_path2, win_id)
                        new_b64 = base64.standard_b64encode(new_bytes).decode("utf-8")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": [{
                                "type": "image",
                                "source": {"type": "base64", "media_type": "image/jpeg", "data": new_b64}
                            }]
                        })
                    else:
                        execute_action(action, win_x, win_y)
                        time.sleep(0.8)
                        # After action, take screenshot for tool result
                        shot_path3 = str(RESULTS_DIR / f"step_{step:03d}c_{run_id}.png")
                        new_bytes = take_screenshot(shot_path3, win_id)
                        new_b64 = base64.standard_b64encode(new_bytes).decode("utf-8")
                        screenshot_paths.append(shot_path3)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": [{
                                "type": "image",
                                "source": {"type": "base64", "media_type": "image/jpeg", "data": new_b64}
                            }]
                        })

                messages.append({"role": "user", "content": tool_results})

            elif stop_reason == "end_turn":
                print("\n✅ Agent completed task (end_turn)")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()

    # Generate MP4 from screenshots
    print(f"\n📸 Collected {len(screenshot_paths)} screenshots")
    if screenshot_paths:
        mp4_path = str(RESULTS_DIR / f"sage_demo_{run_id}.mp4")
        valid_shots = [p for p in screenshot_paths if Path(p).exists()]
        if valid_shots:
            # Create file list for ffmpeg
            filelist = "/tmp/freerdp_frames.txt"
            with open(filelist, "w") as f:
                for p in valid_shots:
                    f.write(f"file '{p}'\nduration 1.5\n")
            subprocess.run([
                "/opt/homebrew/bin/ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", filelist,
                "-vf", "fps=2,scale=1280:720:flags=lanczos",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                mp4_path
            ], capture_output=True)
            if Path(mp4_path).exists():
                size_mb = Path(mp4_path).stat().st_size / 1024 / 1024
                print(f"🎬 MP4 saved: {mp4_path} ({size_mb:.1f} MB)")
            else:
                print("⚠️  MP4 generation failed")

    print(f"\nResults in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
