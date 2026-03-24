"""
Take a screenshot of a Windows machine via RDP using aardwolf.
"""
import asyncio
import sys
import os

from aardwolf import RDPConnection
from aardwolf.commons.url import RDPConnectionURL


async def take_rdp_screenshot(host, port, username, password, output_path):
    """Connect via RDP and take a screenshot."""
    url = f"rdp+ntlm-password://{username}:{password}@{host}:{port}/?dc="

    print(f"Connecting to {host}:{port} as {username}...")
    conn_url = RDPConnectionURL(url)
    conn = conn_url.get_connection(None)

    _, err = await conn.connect()
    if err:
        print(f"Connection error: {err}")
        return False

    print("Connected! Waiting for desktop...")
    await asyncio.sleep(5)

    print("Taking screenshot...")
    # Get the framebuffer
    if hasattr(conn, 'desktop_buffer') and conn.desktop_buffer:
        from PIL import Image
        img = Image.frombytes('RGBA', (conn.desktop_buffer_width, conn.desktop_buffer_height), conn.desktop_buffer)
        img.save(output_path)
        print(f"Screenshot saved to {output_path}")
    else:
        print("No desktop buffer available")

    await conn.disconnect()
    return True


if __name__ == "__main__":
    host = os.environ.get("SAGE_VM_IP", "34.175.136.176")
    port = 3389
    username = os.environ.get("SAGE_VM_USER", "albert")
    password = os.environ.get("SAGE_VM_PASS", "")

    if not password:
        print("Set SAGE_VM_PASS environment variable")
        sys.exit(1)

    output = sys.argv[1] if len(sys.argv) > 1 else "rdp_screenshot.png"

    asyncio.run(take_rdp_screenshot(host, port, username, password, output))
