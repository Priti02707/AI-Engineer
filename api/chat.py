"""Run the repository's four engineering exercises through a server-side API."""

import hmac
import json
import os
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_BODY = 80_000
MAX_PROMPT = 2_000
TICKET_FIELDS = ("name", "email", "issue")
TICKET_SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in TICKET_FIELDS},
    "required": list(TICKET_FIELDS),
    "additionalProperties": False,
}
MODES = ("chat", "persona", "tokens", "ticket")


def credentials():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    code = os.environ.get("DEMO_ACCESS_CODE", "").strip()
    if not key or not 24 <= len(code) <= 128 or not code.isascii():
        return "", ""
    return key, code


def validated_text(value, limit, label):
    if not isinstance(value, str) or not 0 < len(value.strip()) <= limit:
        raise ValueError(f"{label} must contain 1–{limit} characters.")
    return value.strip()


def exercise_options(body):
    if not isinstance(body, dict):
        raise ValueError("Send a JSON object.")
    mode = body.get("mode")
    if mode not in MODES:
        raise ValueError("Choose one of the four exercises.")
    if mode == "tokens":
        prompts = body.get("prompts")
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
            raise ValueError("Enter one to three prompts, one per line.")
        return mode, [validated_text(prompt, MAX_PROMPT, "Each prompt") for prompt in prompts], {}
    prompt = validated_text(body.get("prompt"), MAX_PROMPT, "Prompt")
    if mode != "persona":
        return mode, [prompt], {}
    system = validated_text(body.get("system"), 1_000, "System instruction")
    temperature = body.get("temperature")
    if type(temperature) not in (float, int) or not 0 <= temperature <= 2:
        raise ValueError("Temperature must be a number from 0 to 2.")
    return mode, [prompt], {"system": system, "temperature": temperature}


def completion(api_key, model, mode, prompt, *, system=None, temperature=None):
    if system is None:
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
    if temperature is not None:
        payload["temperature"] = temperature
    if mode == "ticket":
        payload["response_format"] = {"type": "json_object"}
        if model == DEFAULT_MODEL:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "support_ticket", "strict": True, "schema": TICKET_SCHEMA,
            }}

    request = Request(
        GROQ_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    request.add_unredirected_header("Authorization", f"Bearer {api_key}")
    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read(131_072))

    choice = data["choices"][0]
    result = choice["message"]["content"]
    if mode == "tokens":
        usage = data["usage"]
        fields = ("prompt_tokens", "completion_tokens", "total_tokens")
        counts = {field: usage[field] for field in fields}
        if any(type(count) is not int or count < 0 for count in counts.values()):
            raise ValueError("Invalid token usage")
        return {
            **counts,
            "prompt": prompt,
            "finish_reason": choice.get("finish_reason"),
            "response": result if isinstance(result, str) else "",
        }
    if not isinstance(result, str) or not result.strip():
        raise ValueError("Empty completion")
    if mode != "ticket":
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

    def do_GET(self):
        key, _ = credentials()
        self.respond(200, {"live_enabled": bool(key)})

    def do_POST(self):
        api_key, access_code = credentials()
        if not api_key:
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
        try:
            mode, prompts, options = exercise_options(data)
        except ValueError as error:
            self.respond(400, {"error": str(error)})
            return

        model = os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_MODEL
        try:
            if mode == "tokens":
                with ThreadPoolExecutor(max_workers=len(prompts)) as pool:
                    result = list(pool.map(lambda prompt: completion(api_key, model, mode, prompt), prompts))
            else:
                result = completion(api_key, model, mode, prompts[0], **options)
        except HTTPError as error:
            status = 429 if error.code == 429 else 502
            error.close()
            message = "Groq is rate limiting requests. Try again later." if status == 429 else "Groq could not complete the request."
            self.respond(status, {"error": message})
            return
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            self.respond(502, {"error": "Groq did not return a valid response."})
            return
        self.respond(200, {"result": result, "model": model})
