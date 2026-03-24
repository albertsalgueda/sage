"""
Simple VNC screenshot tool using vncdotool.
Takes a screenshot of the VNC server desktop.
"""
import sys
import os
sys.path.insert(0, os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages"))

from vncdotool.client import VNCDoToolFactory, VNCDoToolClient
from twisted.internet import reactor, defer
from PIL import Image
import time


def take_vnc_screenshot(host, port, password, output_path, timeout=30):
    """Take a screenshot via VNC using Twisted reactor."""

    factory = VNCDoToolFactory()
    factory.password = password.encode() if isinstance(password, str) else password

    d = defer.Deferred()

    class ScreenshotClient(VNCDoToolClient):
        def vncConnectionMade(self):
            print("VNC connection established!")
            # Wait a bit for the screen to render
            reactor.callLater(2, self.do_capture)

        def do_capture(self):
            print("Capturing screen...")
            self.captureScreen(output_path).addCallback(self.on_capture)

        def on_capture(self, result):
            print(f"Screenshot saved to: {output_path}")
            self.transport.loseConnection()
            d.callback(True)

    factory.protocol = ScreenshotClient

    connector = reactor.connectTCP(host, port, factory, timeout=timeout)

    def on_timeout():
        if not d.called:
            print("Timeout!")
            connector.disconnect()
            d.errback(Exception("Timeout"))

    reactor.callLater(timeout, on_timeout)

    def stop(result):
        reactor.stop()
        return result

    d.addBoth(stop)
    reactor.run()


if __name__ == "__main__":
    host = os.environ.get("SAGE_VM_IP", "34.175.136.176")
    port = 5900
    password = "sage2026"
    output = sys.argv[1] if len(sys.argv) > 1 else "vnc_screenshot.png"

    print(f"Connecting to {host}:{port}...")
    take_vnc_screenshot(host, port, password, output)
