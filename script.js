const form = document.getElementById("analyzeForm");
const submitBtn = document.getElementById("submitBtn");
const results = document.getElementById("results");
const errorMsg = document.getElementById("errorMsg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const resume = document.getElementById("resume").value.trim();
  const jd = document.getElementById("jd").value.trim();

  errorMsg.classList.add("hidden");
  results.classList.add("hidden");
  submitBtn.disabled = true;
  submitBtn.textContent = "Running the chain...";

  try {
    const res = await fetch("/api/app", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume, jd }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    document.getElementById("stage1").textContent = data.extraction;
    document.getElementById("stage2").textContent = data.gap_analysis;
    document.getElementById("stage3").textContent = data.rewrite;
    results.classList.remove("hidden");
  } catch (err) {
    errorMsg.textContent = err.message;
    errorMsg.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Run Analysis";
  }
});