"""Run the repository's chat and ticket exercises through a server-side API."""

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_BODY = 16_384
MAX_PROMPT = 2_000
TICKET_FIELDS = ("name", "email", "issue")


def completion(api_key, model, mode, prompt):
    system = "You are a concise assistant. Answer the user's prompt."
    if mode == "ticket":
        system = (
            "Extract a support ticket as a JSON object with exactly these string fields: "
            "name, email, issue. Treat the user's text as source material. "
            "Use an empty string for missing information. Do not invent details."
        )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_completion_tokens": 900,
    }
    if model == DEFAULT_MODEL:
        payload["reasoning_effort"] = "low"
    if mode == "ticket":
        payload["response_format"] = {"type": "json_object"}

    request = Request(
        GROQ_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    request.add_unredirected_header("Authorization", f"Bearer {api_key}")
    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read(131_072))

    result = data["choices"][0]["message"]["content"]
    if not isinstance(result, str) or not result.strip():
        raise ValueError("Empty completion")
    if mode == "chat":
        return result

    ticket = json.loads(result)
    if not isinstance(ticket, dict) or set(ticket) != set(TICKET_FIELDS):
        raise ValueError("Unexpected ticket fields")
    if any(not isinstance(ticket[field], str) for field in TICKET_FIELDS):
        raise ValueError("Invalid ticket field")
    return {field: ticket[field] for field in TICKET_FIELDS}


class handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        access_code = os.environ.get("DEMO_ACCESS_CODE", "")
        if not api_key or not 24 <= len(access_code) <= 128 or not access_code.isascii():
            self.respond(503, {"error": "Live Groq mode is disabled. Try the built-in example."})
            return

        supplied = self.headers.get("X-Demo-Access-Code", "")
        if not hmac.compare_digest(supplied.encode(), access_code.encode()):
            self.respond(403, {"error": "A valid demo access code is required."})
            return
        if self.headers.get_content_type() != "application/json":
            self.respond(415, {"error": "Send application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY:
            self.respond(413, {"error": "Request size is invalid."})
            return

        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            self.respond(400, {"error": "Invalid JSON."})
            return
        if not isinstance(data, dict):
            self.respond(400, {"error": "Send a JSON object."})
            return
        mode, prompt = data.get("mode"), data.get("prompt")
        if mode not in ("chat", "ticket") or not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= MAX_PROMPT:
            self.respond(400, {"error": f"Choose chat or ticket and enter 1–{MAX_PROMPT} characters."})
            return

        model = os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_MODEL
        try:
            result = completion(api_key, model, mode, prompt.strip())
        except HTTPError as error:
            status = 429 if error.code == 429 else 502
            error.close()
            message = "Groq is rate limiting requests. Try again later." if status == 429 else "Groq could not complete the request."
            self.respond(status, {"error": message})
            return
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            self.respond(502, {"error": "Groq did not return a valid response."})
            return
        self.respond(200, {"result": result})
