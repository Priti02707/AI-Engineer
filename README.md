# AI Engineering Exercises

Python exercises organized by day. Use Python 3.11 and run each exercise from its own directory.

- **Day 1** · Run `uv run python hello_llm.py` from `day1/` to try a Groq chat completion.
- **Day 2** · Activate a fresh Python virtual environment in `day2/`, run `python -m pip install groq python-dotenv`, then run `python sys_temp.py`.
- **Day 3** · Run `uv run python tokens.py` from `day3/` for the token exercise.
- **Day 4** · Run `uv run python json_pydantic.py` from `day4/` for the structured response exercise.

Set `GROQ_API_KEY` in your environment before running examples that call Groq. Keep local environment files and virtual environments out of Git.

## Web demo and deployment

Run `python serve.py` from the repository root and open <http://127.0.0.1:8000>. The web demo uses Python 3.12 and the standard library. It has built-in examples for chat and ticket extraction that work without credentials.

To host it, import this repository into Vercel with the root directory set to the repository root. The checked-in configuration serves `public/` and runs `api/chat.py` as a Python function.

| Server environment variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Enables live model requests together with the access code. |
| `DEMO_ACCESS_CODE` | Private access code, 24–128 ASCII characters. Use a random value such as one from `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Share it only with intended testers. |
| `GROQ_MODEL` | Optional model override. Defaults to `openai/gpt-oss-20b`. Choose a Groq chat model that supports JSON Object Mode to use both exercises. |

Set these variables in Vercel's project settings or export them in the shell before local testing. Leave both secrets unset for a sample-only public demo. Live requests require the access code, and the Groq key stays server-side. Test both built-in examples and, if configured, run chat and ticket extraction with synthetic inputs. The ticket response is validated against the same three fields used in the Day 4 exercise.
