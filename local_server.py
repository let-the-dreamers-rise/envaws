"""Local dev server: serves frontend/ and routes /api/* to the same Lambda handler used in AWS.

    pip install -r backend/requirements.txt
    python local_server.py            # http://localhost:8080
"""

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("LOCAL_DATA_DIR", os.path.join(ROOT, ".localdata"))

from cleanhour import api  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(ROOT, "frontend"), **kwargs)

    def _api(self, method):
        parts = urlsplit(self.path)
        length = int(self.headers.get("content-length") or 0)
        event = {
            "rawPath": parts.path,
            "queryStringParameters": dict(parse_qsl(parts.query)) or None,
            "requestContext": {"http": {"method": method}},
            "body": self.rfile.read(length).decode() if length else None,
        }
        out = api.handler(event)
        self.send_response(out["statusCode"])
        for k, v in out["headers"].items():
            self.send_header(k, v)
        body = out["body"].encode()
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._api("GET")
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._api("POST")
        self.send_error(404)

    def do_OPTIONS(self):
        return self._api("OPTIONS")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"CleanHour local: http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
