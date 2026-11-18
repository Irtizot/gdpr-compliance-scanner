import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def wait_for_port(port, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


server = subprocess.Popen([sys.executable, str(HERE / "server.py")], cwd=str(HERE))
try:
    if not wait_for_port(8765):
        raise SystemExit("The test server did not start")
    for script in ("py_run.py", "ext_run.py"):
        result = subprocess.run([sys.executable, str(HERE / script)], cwd=str(HERE))
        if result.returncode != 0:
            raise SystemExit(f"{script} failed")
    compare = subprocess.run([sys.executable, str(HERE / "compare.py")], cwd=str(HERE),
                             capture_output=True, text=True)
    output = compare.stdout + compare.stderr
    print(output)
    (HERE / "compare_output.txt").write_text(output, encoding="utf-8")
finally:
    server.terminate()