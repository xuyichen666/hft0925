#!/usr/bin/env python3
"""Bloomberg-style monitor: static UI + live /api/snapshot from JSONL logs."""

from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from asq_snap25.monitor.parse_log import FX_DEFAULT, find_latest_log, parse_log

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
DEFAULT_PORT = 8765


class MonitorHandler(BaseHTTPRequestHandler):
    log_path: Path | None = None
    fx: float = FX_DEFAULT

    def log_message(self, fmt: str, *args) -> None:
        # quieter server logs
        pass

    def _send_json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/snapshot":
            qs = parse_qs(parsed.query)
            fx = float(qs.get("fx", [str(self.fx)])[0])
            try:
                log = self.log_path or find_latest_log()
                snap = parse_log(log, fx=fx)
                self._send_json(asdict(snap))
            except Exception as exc:
                self._send_json({"error": str(exc)}, code=500)
            return

        if parsed.path in ("/", "/index.html"):
            return self._send_file(STATIC / "index.html")

        rel = parsed.path.lstrip("/")
        target = (STATIC / rel).resolve()
        if not str(target).startswith(str(STATIC.resolve())):
            self.send_error(403)
            return
        return self._send_file(target)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


def main() -> None:
    ap = argparse.ArgumentParser(description="ASQ-snap25 Bloomberg monitor server")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--log", type=Path, help="jsonl log path (default: latest in logs/)")
    ap.add_argument("--fx", type=float, default=FX_DEFAULT, help="USDT→CNY rate")
    args = ap.parse_args()

    MonitorHandler.log_path = args.log
    MonitorHandler.fx = args.fx
    log = args.log or find_latest_log()
    print(f"ASQ-snap25 Monitor → http://127.0.0.1:{args.port}")
    print(f"log: {log}")
    print(f"fx:  {args.fx} CNY/USDT")
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), MonitorHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
