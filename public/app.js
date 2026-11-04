const lessons = {
  chat: {
    note: "Send a user prompt and inspect the model’s plain-text reply.",
    label: "Prompt",
    prompt: "Explain a system prompt and a user prompt in two sentences.",
    result: "A system prompt sets the assistant’s role and instructions. A user prompt states what the assistant should do now.",
  },
  persona: {
    note: "Edit the system instruction to steer the answer. Try the same prompt with two temperature values to compare the replies.",
    label: "User prompt",
    system: "You are a brand strategist. Suggest one name and explain it in one sentence.",
    prompt: "Name a food business that makes lentil snacks.",
    result: "LentilLift — the name pairs the main ingredient with the quick energy of a snack.",
  },
  tokens: {
    note: "Enter up to three prompts, one per line. Compare Groq’s reported usage and finish reasons. Input counts include instructions, and output counts can include model reasoning.",
    label: "Prompts (one per line)",
    prompt: "Explain binary search in one sentence.\nExplain binary search and give a worked example.",
    result: [
      { prompt: "Explain binary search in one sentence.", prompt_tokens: 32, completion_tokens: 38, total_tokens: 70, finish_reason: "stop", response: "Binary search repeatedly halves a sorted range until it finds the target or runs out of candidates." },
      { prompt: "Explain binary search and give a worked example.", prompt_tokens: 35, completion_tokens: 102, total_tokens: 137, finish_reason: "stop", response: "To find 7 in [1, 3, 5, 7, 9], compare it with the middle value, 5. Since 7 is larger, search the right half [7, 9]. The next middle value is 7." },
    ],
  },
  ticket: {
    note: "Extract three string fields: name, email, and issue. Unknown fields are returned as empty strings.",
    label: "Support ticket",
    prompt: "I’m Casey Morgan, reachable at casey@example.com. My keyboard disconnects when my laptop wakes from sleep.",
    result: { name: "Casey Morgan", email: "casey@example.com", issue: "Keyboard disconnects after the laptop wakes from sleep." },
  },
};

const form = document.querySelector("#exercise");
const mode = document.querySelector("#mode");
const promptInput = document.querySelector("#prompt");
const label = document.querySelector("#prompt-label");
const lesson = document.querySelector("#lesson");
const personaFields = document.querySelector("#persona-fields");
const system = document.querySelector("#system");
const temperature = document.querySelector("#temperature");
const availability = document.querySelector("#availability");
const status = document.querySelector("#status");
const output = document.querySelector("#result");
const tokenResults = document.querySelector("#token-results");
const tokenBody = document.querySelector("#token-body");
const tokenReplies = document.querySelector("#token-replies");
const run = document.querySelector("#run");
const sample = document.querySelector("#sample");
let liveEnabled = null;

function show(message, result) {
  status.textContent = message;
  output.textContent = result === undefined || Array.isArray(result)
    ? "" : typeof result === "string" ? result : JSON.stringify(result, null, 2);
  tokenBody.replaceChildren();
  tokenReplies.replaceChildren();
  tokenResults.hidden = !Array.isArray(result);
  if (!Array.isArray(result)) return;
  result.forEach((row, index) => {
    const tr = document.createElement("tr");
    const prompt = document.createElement("th");
    prompt.scope = "row";
    prompt.textContent = String(index + 1);
    tr.append(prompt);
    for (const field of ["prompt_tokens", "completion_tokens", "total_tokens", "finish_reason"]) {
      const cell = document.createElement("td");
      cell.textContent = row[field] ?? "—";
      tr.append(cell);
    }
    tokenBody.append(tr);

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `Prompt ${index + 1}: ${row.prompt}`;
    const reply = document.createElement("pre");
    reply.textContent = row.response || "No answer text was returned.";
    details.append(summary, reply);
    tokenReplies.append(details);
  });
}

function selectLesson() {
  const current = lessons[mode.value];
  const persona = mode.value === "persona";
  personaFields.hidden = !persona;
  system.disabled = temperature.disabled = !persona;
  system.required = temperature.required = persona;
  system.value = current.system || "";
  temperature.value = "1";
  label.textContent = current.label;
  lesson.textContent = current.note;
  promptInput.value = "";
  promptInput.maxLength = mode.value === "tokens" ? 6002 : 2000;
  show("Show a built-in example or run your own input.");
}

mode.addEventListener("change", selectLesson);
selectLesson();

sample.addEventListener("click", () => {
  const example = lessons[mode.value];
  promptInput.value = example.prompt;
  if (mode.value === "persona") {
    system.value = example.system;
    temperature.value = "1";
  }
  show(mode.value === "tokens" ? "Built-in example · illustrative token counts" : "Built-in example output", example.result);
});

fetch("/api/chat", { signal: AbortSignal.timeout(5000) })
  .then(response => {
    if (!response.ok) throw new Error("Live status unavailable");
    return response.json();
  })
  .then(data => {
    liveEnabled = data.live_enabled;
    availability.textContent = liveEnabled
      ? "Live Groq is enabled. Run an exercise to send a request."
      : "Live Groq is disabled. All four built-in examples are available.";
  })
  .catch(() => { availability.textContent = "The live API status is unavailable. Built-in examples still work."; });

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (run.disabled) return;
  if (liveEnabled === false) {
    show("Live Groq is disabled. Try a built-in example.");
    return;
  }

  const payload = { mode: mode.value };
  if (mode.value === "tokens") {
    payload.prompts = promptInput.value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (!payload.prompts.length || payload.prompts.length > 3 || payload.prompts.some(line => line.length > 2000)) {
      show("Enter one to three prompts, with up to 2,000 characters per line.");
      return;
    }
  } else {
    payload.prompt = promptInput.value.trim();
  }
  if (mode.value === "persona") {
    payload.system = system.value.trim();
    payload.temperature = temperature.valueAsNumber;
  }

  run.disabled = mode.disabled = sample.disabled = true;
  show("Waiting for Groq…");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(28_000),
    });
    const data = await response.json();
    if (!response.ok) {
      show(data.error || "Live request failed. Try the built-in example.");
      return;
    }
    show(data.model ? `Live Groq output · ${data.model}` : "Live Groq output", data.result);
  } catch {
    show("The demo could not reach the live service. Try the built-in example.");
  } finally {
    run.disabled = mode.disabled = sample.disabled = false;
  }
});
