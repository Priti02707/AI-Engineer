const examples = {
  chat: {
    prompt: "Explain the difference between a system prompt and a user prompt in two sentences.",
    result: "A system prompt sets the assistant’s role and operating instructions. A user prompt states the specific request the assistant should answer.",
  },
  ticket: {
    prompt: "I’m Casey Morgan, reachable at casey@example.com. My keyboard disconnects when my laptop wakes from sleep.",
    result: { name: "Casey Morgan", email: "casey@example.com", issue: "Keyboard disconnects after the laptop wakes from sleep." },
  },
};

const form = document.querySelector("#exercise");
const mode = document.querySelector("#mode");
const promptInput = document.querySelector("#prompt");
const code = document.querySelector("#code");
const status = document.querySelector("#status");
const output = document.querySelector("#result");
const run = document.querySelector("#run");
const sample = document.querySelector("#sample");

function show(message, result = "") {
  status.textContent = message;
  output.textContent = typeof result === "string" ? result : JSON.stringify(result, null, 2);
}

sample.addEventListener("click", () => {
  const example = examples[mode.value];
  promptInput.value = example.prompt;
  show("Built-in example output", example.result);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  run.disabled = true;
  mode.disabled = true;
  sample.disabled = true;
  show("Waiting for Groq…");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Demo-Access-Code": code.value },
      body: JSON.stringify({ mode: mode.value, prompt: promptInput.value }),
      signal: AbortSignal.timeout(28_000),
    });
    const data = await response.json();
    if (!response.ok) {
      show(data.error || "Live request failed. Try the built-in example.");
      return;
    }
    show("Live Groq output", data.result);
  } catch {
    show("The demo could not reach the live service. Try the built-in example.");
  } finally {
    run.disabled = false;
    mode.disabled = false;
    sample.disabled = false;
  }
});
