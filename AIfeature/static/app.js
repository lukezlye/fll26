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
