import json
import os
from functools import partial
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from api.chat import DEFAULT_MODEL, completion, exercise_options
from serve import LocalHandler


class ExerciseTests(TestCase):
    def test_persona_bounds_and_token_batch_limit(self):
        for temperature in (True, "1", -1, 2.1, float("nan")):
            with self.subTest(temperature=temperature), self.assertRaises(ValueError):
                exercise_options({"mode": "persona", "system": "Tutor", "prompt": "Help", "temperature": temperature})
        for prompts in ([], ["example"] * 4, ["x" * 2001], [" "]):
            with self.subTest(prompts=len(prompts)), self.assertRaises(ValueError):
                exercise_options({"mode": "tokens", "prompts": prompts})

    def test_ticket_modes_enforce_expected_fields(self):
        ticket = {"name": "Casey", "email": "", "issue": "Broken keyboard"}
        for model, response_type in ((DEFAULT_MODEL, "json_schema"), ("alternative", "json_object")):
            with self.subTest(model=model):
                encoded = json.dumps({"choices": [{"message": {"content": json.dumps(ticket)}}]}).encode()
                with patch("api.chat.urlopen", return_value=BytesIO(encoded)) as call:
                    self.assertEqual(completion("test", model, "ticket", "Synthetic ticket"), ticket)
                    payload = json.loads(call.call_args.args[0].data)
                self.assertEqual(payload["response_format"]["type"], response_type)
                if response_type == "json_schema":
                    schema = payload["response_format"]["json_schema"]
                    self.assertTrue(schema["strict"])
                    self.assertEqual(schema["schema"]["required"], list(ticket))
        invalid = b'{"choices":[{"message":{"content":"{}"}}]}'
        with patch("api.chat.urlopen", return_value=BytesIO(invalid)):
            with self.assertRaises(ValueError):
                completion("test", DEFAULT_MODEL, "ticket", "Synthetic ticket")

    def test_local_http_all_four_lessons_with_only_server_key(self):
        def groq_reply(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            system, user = [item["content"] for item in payload["messages"]]
            if "response_format" in payload:
                content = '{"name":"Casey","email":"","issue":"Keyboard"}'
            elif system == "Act as a tutor":
                self.assertEqual(payload["temperature"], 0.25)
                content = "Tutor reply"
            else:
                content = "Reply to " + user
            return BytesIO(json.dumps({
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
            }).encode())

        with ThreadingHTTPServer(("127.0.0.1", 0), partial(LocalHandler, directory="public")) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            client = build_opener(ProxyHandler({}))

            def post(payload):
                request = Request(base + "/api/chat", data=json.dumps(payload).encode(), headers={
                    "Content-Type": "application/json",
                })
                try:
                    response = client.open(request, timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    return response.status, json.load(response)

            try:
                for path in ("/", "/app.js", "/styles.css"):
                    with client.open(base + path, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                chat = {"mode": "chat", "prompt": "Hello"}
                with patch.dict(os.environ, {}, clear=True):
                    with client.open(base + "/api/chat", timeout=5) as response:
                        self.assertEqual(json.load(response), {"live_enabled": False})
                    self.assertEqual(post(chat)[0], 503)
                env = {"GROQ_API_KEY": "test-key"}
                with patch.dict(os.environ, env, clear=True), patch("api.chat.urlopen", side_effect=groq_reply) as provider:
                    with client.open(base + "/api/chat", timeout=5) as response:
                        self.assertEqual(json.load(response), {"live_enabled": True})
                    self.assertEqual(post({"mode": "tokens", "prompts": ["x"] * 4})[0], 400)
                    provider.assert_not_called()
                    self.assertEqual(post(chat)[1]["result"], "Reply to Hello")
                    persona = {"mode": "persona", "prompt": "Help", "system": "Act as a tutor", "temperature": 0.25}
                    self.assertEqual(post(persona)[1]["result"], "Tutor reply")
                    self.assertEqual(post({"mode": "ticket", "prompt": "Synthetic example"})[1]["result"]["email"], "")
                    status, payload = post({"mode": "tokens", "prompts": ["short", "long", "third"]})
                    self.assertEqual(status, 200)
                    self.assertEqual([row["prompt"] for row in payload["result"]], ["short", "long", "third"])
                    self.assertTrue(all(row["total_tokens"] == 7 for row in payload["result"]))
            finally:
                server.shutdown()
                worker.join()
