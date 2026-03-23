#!/usr/bin/env python3
"""
Experiment 2: Sage 200 Computer-Use Agent
==========================================
Uses Anthropic's computer-use API to control a Sage 200 VM via VNC,
navigating the IDE to create objects (tables, fields, screens, scripts).

Prerequisites:
    - Sage 200 VM running and accessible via VNC
    - VNC connection details in .env file
    - ANTHROPIC_API_KEY set

Usage:
    python scripts/computer_use_sage.py --demo        # Demo mode: navigate to admin console
    python scripts/computer_use_sage.py --screenshot   # Take a screenshot only
    python scripts/computer_use_sage.py --task "Create table CF_Equipos"  # Execute a task
"""

import argparse
import base64
import io
import os
import struct
import sys
import socket
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# Load .env from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

RESULTS_DIR = REPO_ROOT / "results"


@dataclass
class VNCConfig:
    host: str
    port: int
    password: str
    width: int = 1920
    height: int = 1080

    @classmethod
    def from_env(cls) -> "VNCConfig":
        host = os.environ.get("SAGE_VM_HOST", "localhost")
        port = int(os.environ.get("SAGE_VM_VNC_PORT", "5900"))
        password = os.environ.get("SAGE_VM_VNC_PASSWORD", "")
        width = int(os.environ.get("SAGE_VM_SCREEN_WIDTH", "1920"))
        height = int(os.environ.get("SAGE_VM_SCREEN_HEIGHT", "1080"))
        return cls(host=host, port=port, password=password, width=width, height=height)


class VNCClient:
    """Minimal VNC client for screenshot + keyboard/mouse input.

    Implements RFB protocol basics:
    - Handshake & VNC authentication
    - Framebuffer update requests (screenshots)
    - Key events and pointer events (mouse click/move)
    """

    def __init__(self, config: VNCConfig):
        self.config = config
        self.sock = None
        self.width = config.width
        self.height = config.height
        self.connected = False

    def connect(self):
        """Connect to VNC server and complete handshake."""
        print(f"Connecting to VNC: {self.config.host}:{self.config.port}...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.config.host, self.config.port))

        # RFB protocol version handshake
        server_version = self.sock.recv(12)
        print(f"  Server version: {server_version.decode().strip()}")
        self.sock.send(b"RFB 003.008\n")

        # Security type negotiation
        num_types = struct.unpack("!B", self.sock.recv(1))[0]
        if num_types == 0:
            # Connection failed
            msg_len = struct.unpack("!I", self.sock.recv(4))[0]
            msg = self.sock.recv(msg_len).decode()
            raise ConnectionError(f"VNC connection refused: {msg}")

        sec_types = self.sock.recv(num_types)

        if 1 in sec_types:
            # No authentication
            self.sock.send(bytes([1]))
        elif 2 in sec_types:
            # VNC authentication
            self.sock.send(bytes([2]))
            self._vnc_auth()
        else:
            raise ConnectionError(f"No supported security types: {list(sec_types)}")

        # Security result
        result = struct.unpack("!I", self.sock.recv(4))[0]
        if result != 0:
            raise ConnectionError("VNC authentication failed")

        # Client init (shared flag = 1)
        self.sock.send(bytes([1]))

        # Server init
        server_init = self.sock.recv(24)
        self.width = struct.unpack("!H", server_init[0:2])[0]
        self.height = struct.unpack("!H", server_init[2:4])[0]
        name_len = struct.unpack("!I", server_init[20:24])[0]
        if name_len > 0:
            self.sock.recv(name_len)  # Desktop name

        print(f"  Connected! Desktop: {self.width}x{self.height}")
        self.connected = True

    def _vnc_auth(self):
        """Handle VNC DES challenge-response authentication."""
        challenge = self.sock.recv(16)
        if not self.config.password:
            raise ConnectionError("VNC password required but not set in .env")

        # VNC uses a DES key derived from the password (reversed bit order per byte)
        key = self.config.password.encode("ascii")[:8].ljust(8, b"\x00")
        # Reverse bits in each byte (VNC quirk)
        key = bytes(int(f"{b:08b}"[::-1], 2) for b in key)

        try:
            from Crypto.Cipher import DES
            des = DES.new(key, DES.MODE_ECB)
            response = des.encrypt(challenge[:8]) + des.encrypt(challenge[8:16])
        except ImportError:
            # Fallback: try pyDes
            try:
                import pyDes
                des = pyDes.des(key, pyDes.ECB)
                response = des.encrypt(challenge)
            except ImportError:
                raise ImportError(
                    "VNC authentication requires pycryptodome or pyDes. "
                    "Install with: pip install pycryptodome"
                )

        self.sock.send(response)

    def screenshot(self) -> bytes:
        """Request a full framebuffer update and return as PNG bytes."""
        if not self.connected:
            raise ConnectionError("Not connected to VNC")

        # Request framebuffer update (incremental=0 for full)
        msg = struct.pack("!BxHHHH", 3, 0, 0, self.width, self.height)
        self.sock.send(msg)

        # Read framebuffer update response
        # This is simplified — a production client would handle all message types
        header = self.sock.recv(1)
        msg_type = struct.unpack("!B", header)[0]

        if msg_type != 0:  # Not a framebuffer update
            print(f"  Unexpected message type: {msg_type}")
            return b""

        self.sock.recv(1)  # padding
        num_rects = struct.unpack("!H", self.sock.recv(2))[0]

        # Collect pixel data (simplified for raw encoding)
        pixels = bytearray(self.width * self.height * 4)
        for _ in range(num_rects):
            rect_header = self.sock.recv(12)
            x, y, w, h, encoding = struct.unpack("!HHHHi", rect_header)

            if encoding == 0:  # Raw
                data_len = w * h * 4  # Assuming 32-bit color
                data = b""
                while len(data) < data_len:
                    chunk = self.sock.recv(min(data_len - len(data), 65536))
                    if not chunk:
                        break
                    data += chunk

                # Copy to pixel buffer
                for row in range(h):
                    src_offset = row * w * 4
                    dst_offset = ((y + row) * self.width + x) * 4
                    pixels[dst_offset:dst_offset + w * 4] = data[src_offset:src_offset + w * 4]

        # Convert to PNG using PIL
        try:
            from PIL import Image
            img = Image.frombytes("RGBA", (self.width, self.height), bytes(pixels))
            img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            print("WARNING: Pillow not installed, returning raw pixel data")
            return bytes(pixels)

    def key_event(self, key: int, down: bool = True):
        """Send a key press/release event."""
        msg = struct.pack("!BBxxI", 4, 1 if down else 0, key)
        self.sock.send(msg)

    def type_text(self, text: str):
        """Type a string by sending key press/release for each character."""
        for char in text:
            code = ord(char)
            self.key_event(code, down=True)
            self.key_event(code, down=False)
            time.sleep(0.02)

    def mouse_move(self, x: int, y: int):
        """Move mouse to coordinates."""
        msg = struct.pack("!BBHH", 5, 0, x, y)
        self.sock.send(msg)

    def mouse_click(self, x: int, y: int, button: int = 1):
        """Click at coordinates. button: 1=left, 2=middle, 4=right."""
        self.mouse_move(x, y)
        time.sleep(0.05)
        # Press
        msg = struct.pack("!BBHH", 5, button, x, y)
        self.sock.send(msg)
        time.sleep(0.1)
        # Release
        msg = struct.pack("!BBHH", 5, 0, x, y)
        self.sock.send(msg)

    def disconnect(self):
        """Close VNC connection."""
        if self.sock:
            self.sock.close()
            self.connected = False
            print("VNC disconnected.")


class SageComputerUseAgent:
    """Agent that uses Anthropic's computer-use API to control Sage 200 via VNC."""

    def __init__(self, vnc: VNCClient, model: str = "claude-sonnet-4-20250514"):
        self.vnc = vnc
        self.model = model
        self.client = anthropic.Anthropic()
        self.messages = []

    def get_screenshot_b64(self) -> str:
        """Take a VNC screenshot and return as base64 PNG."""
        png_data = self.vnc.screenshot()
        return base64.standard_b64encode(png_data).decode("ascii")

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a computer-use tool action via VNC."""
        action = tool_input.get("action")

        if action == "screenshot":
            b64 = self.get_screenshot_b64()
            return f"Screenshot taken ({self.vnc.width}x{self.vnc.height})"

        elif action == "left_click":
            x, y = tool_input["coordinate"]
            self.vnc.mouse_click(int(x), int(y), button=1)
            time.sleep(0.5)
            return f"Clicked at ({x}, {y})"

        elif action == "right_click":
            x, y = tool_input["coordinate"]
            self.vnc.mouse_click(int(x), int(y), button=4)
            time.sleep(0.5)
            return f"Right-clicked at ({x}, {y})"

        elif action == "double_click":
            x, y = tool_input["coordinate"]
            self.vnc.mouse_click(int(x), int(y))
            time.sleep(0.1)
            self.vnc.mouse_click(int(x), int(y))
            time.sleep(0.5)
            return f"Double-clicked at ({x}, {y})"

        elif action == "type":
            text = tool_input["text"]
            self.vnc.type_text(text)
            return f"Typed: {text[:50]}..."

        elif action == "key":
            # Map common key names to X11 keysyms
            key_map = {
                "Return": 0xFF0D, "Escape": 0xFF1B, "Tab": 0xFF09,
                "BackSpace": 0xFF08, "Delete": 0xFFFF,
                "Left": 0xFF51, "Up": 0xFF52, "Right": 0xFF53, "Down": 0xFF54,
                "Home": 0xFF50, "End": 0xFF57, "Page_Up": 0xFF55, "Page_Down": 0xFF56,
                "F1": 0xFFBE, "F2": 0xFFBF, "F3": 0xFFC0, "F4": 0xFFC1,
                "F5": 0xFFC2, "F6": 0xFFC3, "F7": 0xFFC4, "F8": 0xFFC5,
                "Control_L": 0xFFE3, "Alt_L": 0xFFE9, "Shift_L": 0xFFE1,
            }
            key_name = tool_input["key"]
            keysym = key_map.get(key_name, ord(key_name[0]) if len(key_name) == 1 else 0)
            self.vnc.key_event(keysym, down=True)
            self.vnc.key_event(keysym, down=False)
            return f"Key pressed: {key_name}"

        elif action == "mouse_move":
            x, y = tool_input["coordinate"]
            self.vnc.mouse_move(int(x), int(y))
            return f"Mouse moved to ({x}, {y})"

        elif action == "scroll":
            x, y = tool_input["coordinate"]
            direction = tool_input.get("direction", "down")
            amount = tool_input.get("amount", 3)
            # Scroll via mouse button 4 (up) or 5 (down)
            button = 8 if direction == "up" else 16
            for _ in range(amount):
                msg = struct.pack("!BBHH", 5, button, int(x), int(y))
                self.vnc.sock.send(msg)
                time.sleep(0.05)
                msg = struct.pack("!BBHH", 5, 0, int(x), int(y))
                self.vnc.sock.send(msg)
            return f"Scrolled {direction} at ({x}, {y})"

        else:
            return f"Unknown action: {action}"

    def run_task(self, task: str, max_steps: int = 30) -> list[dict]:
        """Run a computer-use task loop with Claude."""
        system_prompt = """You are controlling a Sage 200 application running on a Windows VM via VNC.
Your goal is to navigate the Sage 200 IDE to complete the requested task.

Key navigation hints for Sage 200:
- The main window has a menu bar at the top
- "Consola de Administracion" is the admin console
- "Herramientas" menu contains "Importar Objetos de Repositorio" and other dev tools
- To create tables/fields: use the admin console developer tools
- The IDE has a tree view on the left for navigating objects

Always start by taking a screenshot to see the current state."""

        self.messages = [{"role": "user", "content": task}]
        actions_log = []

        for step in range(max_steps):
            print(f"\n--- Step {step + 1}/{max_steps} ---")

            # Get screenshot for context
            screenshot_b64 = self.get_screenshot_b64()

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=self.messages,
                tools=[{
                    "type": "computer_20251124",
                    "name": "computer",
                    "display_width_px": self.vnc.width,
                    "display_height_px": self.vnc.height,
                    "display_number": 1,
                }],
                betas=["computer-use-2025-01-24"],
            )

            # Process response
            assistant_content = response.content
            self.messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "end_turn":
                # Model is done
                for block in assistant_content:
                    if hasattr(block, "text"):
                        print(f"  Agent: {block.text}")
                        actions_log.append({"step": step, "type": "message", "text": block.text})
                break

            # Process tool uses
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    print(f"  Tool: {block.name} -> {block.input.get('action', 'unknown')}")
                    result_text = self.execute_tool(block.name, block.input)
                    print(f"  Result: {result_text}")

                    actions_log.append({
                        "step": step,
                        "type": "tool_use",
                        "action": block.input.get("action"),
                        "input": block.input,
                        "result": result_text,
                    })

                    # Build tool result with screenshot
                    tool_result_content = [{"type": "text", "text": result_text}]

                    # Always include a fresh screenshot after actions
                    if block.input.get("action") != "screenshot":
                        time.sleep(0.5)  # Wait for UI to update
                    new_screenshot = self.get_screenshot_b64()
                    tool_result_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": new_screenshot,
                        },
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result_content,
                    })

                elif hasattr(block, "text"):
                    print(f"  Agent: {block.text}")

            if tool_results:
                self.messages.append({"role": "user", "content": tool_results})

        return actions_log


def demo_mode(vnc: VNCClient, model: str):
    """Demo: Navigate to Consola de Administracion > Herramientas."""
    agent = SageComputerUseAgent(vnc, model)

    task = """Take a screenshot first to see the current state of the Sage 200 application.
Then navigate to:
1. Open the "Consola de Administracion" (Admin Console)
2. Go to "Herramientas" (Tools) menu
3. Take a final screenshot showing the available tools

Report what you see at each step."""

    print("=" * 50)
    print("  DEMO MODE: Navigate to Admin Console > Tools")
    print("=" * 50)

    actions = agent.run_task(task, max_steps=15)

    # Save log
    RESULTS_DIR.mkdir(exist_ok=True)
    import json
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = RESULTS_DIR / f"computer_use_demo_{ts}.json"
    log_path.write_text(json.dumps(actions, indent=2, default=str), encoding="utf-8")
    print(f"\nActions log saved: {log_path.name}")


def screenshot_mode(vnc: VNCClient):
    """Just take a screenshot and save it."""
    RESULTS_DIR.mkdir(exist_ok=True)
    png_data = vnc.screenshot()

    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"screenshot_{ts}.png"
    path.write_bytes(png_data)
    print(f"Screenshot saved: {path} ({len(png_data)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Sage 200 Computer-Use Agent")
    parser.add_argument("--demo", action="store_true",
                        help="Demo mode: navigate to Admin Console > Tools")
    parser.add_argument("--screenshot", action="store_true",
                        help="Take a screenshot only")
    parser.add_argument("--task", type=str,
                        help="Custom task to execute")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Anthropic model (default: claude-sonnet-4-20250514)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show config without connecting")
    args = parser.parse_args()

    # Load config
    config = VNCConfig.from_env()

    if args.dry_run:
        print("VNC Configuration:")
        print(f"  Host: {config.host}")
        print(f"  Port: {config.port}")
        print(f"  Password: {'***' if config.password else '(none)'}")
        print(f"  Screen: {config.width}x{config.height}")
        print(f"  Model: {args.model}")
        print("\nReady to connect when VM is available.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Connect to VNC
    vnc = VNCClient(config)
    try:
        vnc.connect()

        if args.screenshot:
            screenshot_mode(vnc)
        elif args.demo:
            demo_mode(vnc, args.model)
        elif args.task:
            agent = SageComputerUseAgent(vnc, args.model)
            actions = agent.run_task(args.task)
            print(f"\nCompleted {len(actions)} actions.")
        else:
            print("No action specified. Use --demo, --screenshot, or --task")
            parser.print_help()

    except ConnectionRefusedError:
        print(f"ERROR: Cannot connect to VNC at {config.host}:{config.port}")
        print("Make sure the Sage VM is running and VNC is enabled.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        vnc.disconnect()


if __name__ == "__main__":
    main()
