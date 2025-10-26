// js/pages/complaint.page.js

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("complaint-form");
  const statusEl = document.getElementById("complaint-status");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const subject = document.getElementById("complaint-subject").value.trim();
    const message = document.getElementById("complaint-message").value.trim();

    if (!subject || !message) {
      statusEl.textContent = "⚠️ Please fill out all fields.";
      statusEl.className = "error";
      return;
    }

    statusEl.textContent = "Sending...";
    statusEl.className = "";

    try {
      const response = await fetch("https://formspree.io/f/YOUR_FORM_ID", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          message,
        }),
      });

      if (response.ok) {
        form.reset();
        statusEl.textContent = "✅ Complaint submitted successfully!";
        statusEl.className = "success";
      } else {
        throw new Error("Server Error");
      }
    } catch (error) {
      statusEl.textContent = "❌ Failed to send. Please try again later.";
      statusEl.className = "error";
      console.error(error);
    }
  });
});
