"use strict";
(() => {
  const data = JSON.parse(document.getElementById("review-data").textContent);
  const form = document.getElementById("decision-form");
  const eligible = data.manifest.approval_eligible === true;
  document.getElementById("approve").disabled = !eligible;
  document.getElementById("gate-message").textContent = eligible
    ? "Validation passed. Human approval is still pending."
    : "Approval is unavailable because this proposal has not passed validation. You can record a rejection.";
  form.addEventListener("submit", event => {
    event.preventDefault();
    const decision = event.submitter && event.submitter.value;
    if (!["approve", "reject"].includes(decision) || !form.reportValidity()) return;
    if (decision === "approve" && !eligible) return;
    const reviewer = document.getElementById("reviewer").value.trim();
    const rationale = document.getElementById("rationale").value.trim();
    if (!reviewer || !rationale) {
      document.getElementById("decision-status").textContent = "Enter your name and a reason for the decision.";
      return;
    }
    const record = {
      decision_version: "1.0", manifest_sha256: data.manifest_sha256,
      source_revision: data.manifest.source_revision, change_id: data.manifest.change_id,
      decision, reviewer, rationale, reviewed_complete_bundle: document.getElementById("ack").checked,
      recorded_at: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(record, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "review-decision.json";
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    document.getElementById("decision-status").textContent = "Decision file exported: " + decision + ". The source checkout is unchanged.";
  });
})();
