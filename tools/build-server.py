"""Build the blog and serve the last successful build while editing its sources."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading


ROOT = Path(__file__).resolve().parents[1]


def inputs():
    paths = [ROOT / "_config.yml", ROOT / "_config.shoka.yml", ROOT / "package.json"]
    for folder in ("source", "tools"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    timestamps = {}
    for path in paths:
        try:
            timestamps[path] = path.stat().st_mtime_ns
        except FileNotFoundError:
            # Editors may atomically rename a file while the directory is scanned.
            continue
    return timestamps


def build():
    return subprocess.run([sys.executable, ROOT / "tools/build-site.py"], cwd=ROOT).returncode == 0


def watch(stop, previous):
    while not stop.wait(1):
        current = inputs()
        if current != previous:
            previous = current
            if not build():
                print("Build failed. Serving the previous output until the next edit.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", "-p", default=4000, type=int)
    parser.add_argument("--host", "-i", default="127.0.0.1")
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), partial(SimpleHTTPRequestHandler, directory=ROOT / "public")) as server:
        initial = inputs()
        if not build():
            return 1
        stop = threading.Event()
        worker = threading.Thread(target=watch, args=(stop, initial), daemon=True)
        worker.start()
        print(f"Preview at http://{args.host}:{server.server_port}/ (watching site sources)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
        return 0


if __name__ == "__main__":
    sys.exit(main())
