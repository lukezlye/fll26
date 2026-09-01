const form = document.querySelector("#risk-form");
const result = document.querySelector("#result");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(form));
  result.innerHTML = "<p>Assessing conditions…</p>";
  const response = await fetch("/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const assessment = await response.json();
  if (!response.ok) {
    result.innerHTML = `<p class="error">${assessment.error}</p>`;
    return;
  }
  result.innerHTML = `
    <p class="score" style="color:${assessment.color}">${assessment.score}<span>/100</span></p>
    <h2>${assessment.level} prevention priority</h2>
    <p><strong>Main factors:</strong> ${assessment.top_factors.join(", ") || "None"}</p>
    <h3>Recommended actions</h3>
    <ul>${assessment.actions.map((action) => `<li>${action}</li>`).join("")}</ul>`;
});

const chatForm = document.querySelector("#chat-form");
const message = document.querySelector("#message");
const conversation = document.querySelector("#conversation");

function addMessage(sender, text, className) {
  const line = document.createElement("p");
  line.className = className;
  const name = document.createElement("strong");
  name.textContent = `${sender}: `;
  line.append(name, text);
  conversation.append(line);
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = message.value.trim();
  if (!question) return;
  addMessage("You", question, "user");
  message.value = "";
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: question }),
  });
  const data = await response.json();
  const reply = response.ok ? data.reply : data.error;
  addMessage("FireWise AI", reply, "bot");
  conversation.scrollTop = conversation.scrollHeight;
});
