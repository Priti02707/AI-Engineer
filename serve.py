"""Serve the web demo locally on a loopback address."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from api.chat import handler


class LocalHandler(handler, SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/chat":
            self.respond(404, {"error": "Unknown endpoint."})
            return
        super().do_POST()


if __name__ == "__main__":
    public = Path(__file__).resolve().parent / "public"
    with ThreadingHTTPServer(("127.0.0.1", 8000), partial(LocalHandler, directory=public)) as server:
        print("Demo available at http://127.0.0.1:8000")
        server.serve_forever()
