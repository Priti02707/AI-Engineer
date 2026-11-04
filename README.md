# AI Engineering Exercises

A four-lesson Python and Groq lab with a browser interface and standalone command-line examples.

| Lesson | What to try in the browser |
| --- | --- |
| Day 1 · Chat completion | Send a prompt and inspect the plain-text response. |
| Day 2 · System prompts and temperature | Edit the system instruction or sampling temperature, then run the same user prompt again to compare responses. |
| Day 3 · Token usage | Submit up to three prompts and compare Groq's input, output, and total token counts, finish reasons, and replies. |
| Day 4 · Structured extraction | Convert a synthetic support ticket to validated JSON with `name`, `email`, and `issue`. |

## Run the web lab

Use Python 3.12 and run `python serve.py` from the repository root. Open <http://127.0.0.1:8000>. All four built-in examples work without credentials. Their output is illustrative, including the sample token counts.

| Server environment variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Enables live exercises together with the demo access code. Keep this key on the server. |
| `DEMO_ACCESS_CODE` | Private, random 24–128 character ASCII code. Enter this code in the browser to authorize live requests. |
| `GROQ_MODEL` | Optional. Defaults to `openai/gpt-oss-20b`. For overrides, use a chat model that supports JSON Object Mode. |

Generate a code with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Export the variables before starting the local server. Live inputs are sent to Groq, so use synthetic data for tickets. The default model uses strict JSON Schema for tickets. Model overrides use JSON Object Mode and the server applies the same field validation. A token comparison makes one model request per prompt, up to three.

## Run the original Python lessons

Export `GROQ_API_KEY` and run each command from the listed directory. The scripts also load an ignored local `.env` file.

| Directory | Command |
| --- | --- |
| `day1/` | `uv run python hello_llm.py` |
| `day2/` | `uv run --with groq --with python-dotenv python sys_temp.py` |
| `day3/` | `uv run python tokens.py` |
| `day4/` | `uv run python json_pydantic.py` |

## Deploy to Vercel

Import the GitHub repository with the root set to the repository root and use the **Other** preset if prompted. The checked-in configuration serves `public/` and runs `api/chat.py` as a Python function. Add the server variables in the Vercel **Production** environment to enable live requests. If you add variables after a deployment, redeploy to load them. Without these variables the site runs as a sample-only lab.

After deployment, open each lesson and load its built-in example. With live mode configured, run a chat prompt, adjust a system instruction, compare two prompts in the token lesson, and submit a synthetic ticket. `GET /api/chat` reports whether live mode is configured.

Run local regression tests with `python -m unittest discover -s tests -v`.
