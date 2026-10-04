from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PREFERRED_PORT = 8501
MAX_PORT = 8599


def root_dir() -> Path:
    # app/launcher.py lives one level below the installation root.
    return Path(__file__).resolve().parents[1]


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def choose_port() -> int:
    for port in range(PREFERRED_PORT, MAX_PORT + 1):
        if port_is_available(port):
            return port
    raise RuntimeError(f"No free local port found in {PREFERRED_PORT}-{MAX_PORT}.")


def open_browser_later(url: str) -> None:
    time.sleep(2.0)
    try:
        webbrowser.open(url, new=1)
    except Exception:
        # Browser auto-open is convenience only. The URL is printed for manual use.
        pass


def main() -> int:
    root = root_dir()
    main_py = root / "app" / "main.py"
    config = root / ".streamlit" / "config.toml"

    if not main_py.is_file():
        print(f"ERROR: application entry point is missing: {main_py}")
        return 1
    if not config.is_file():
        print(f"WARNING: Streamlit config is missing: {config}")

    try:
        port = choose_port()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    url = f"http://{HOST}:{port}"
    print()
    print("Starting Rhodes Planner...")
    print(f"Application root: {root}")
    print(f"Local address:    {url}")
    if port != PREFERRED_PORT:
        print(f"Note: port {PREFERRED_PORT} was busy, using {port} instead.")
    print("Close this window or press Ctrl+C to stop Rhodes Planner.")
    print()

    threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(main_py),
        "--server.address",
        HOST,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]

    try:
        completed = subprocess.run(command, cwd=str(root), check=False)
        return int(completed.returncode)
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        print(f"ERROR: failed to start Streamlit: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
