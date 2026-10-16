"""Starts a local server for a test and checks that it really started.

A free port is picked first and the server started second, so another program can take the port in between.
When that happens the server exits at once; this helper notices and tries a new port instead of letting the
test wait for a page that will never load.
"""

import socket
import subprocess
import time
import urllib.request


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start(make_command, probe="/review.html", tries=5):
    """make_command(port) returns the command list. Returns (process, port) once the server answers."""
    for _ in range(tries):
        port = free_port()
        process = subprocess.Popen(make_command(port), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if process.poll() is not None:  # it could not start, probably because the port was taken
                break
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{probe}", timeout=1).close()
                return process, port
            except OSError:
                time.sleep(0.1)
        process.terminate()
    raise RuntimeError("the test server did not start after several tries")
