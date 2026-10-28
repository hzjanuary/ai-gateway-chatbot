"""Isolated release-test HTTP fixture. Never copied into the release image."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        if self.path != "/api/generate":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/x-ndjson" if body["stream"] else "application/json"
        )
        self.end_headers()
        result = {
            "model": body["model"],
            "response": "offline image transport verified",
            "done": True,
            "eval_count": 5,
            "prompt_eval_count": 3,
        }
        self.wfile.write((json.dumps(result) + "\n").encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 11434), Handler).serve_forever()
