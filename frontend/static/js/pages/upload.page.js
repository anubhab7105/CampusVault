// ===========================
// upload.page.js
// Faculty upload handling
// ===========================
import { isNotEmpty, isValidFileType } from "../lib/validator.js";
import { FILE_TYPES } from "../config.js";
import { getCurrentUser } from "../auth.js";
import { addUploadedFile } from "../state.js";
import { showToast } from "../ui.js";

document.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("upload-form");
  const user = getCurrentUser();

  uploadForm.addEventListener("submit", (e) => {
    e.preventDefault();

    const title = document.getElementById("file-title").value.trim();
    const fileInput = document.getElementById("file-upload");
    const type = document.getElementById("file-type").value;

    if (!isNotEmpty(title) || !fileInput.files.length) {
      showToast("Please fill all fields and select a file", "error");
      return;
    }

    if (!isValidFileType(fileInput.files[0], FILE_TYPES)) {
      showToast("Invalid file type", "error");
      return;
    }

    addUploadedFile({
      title,
      type,
      file: fileInput.files[0].name,
      facultyId: user.userId,
    });

    showToast(`File "${title}" uploaded successfully`);
    uploadForm.reset();
  });
});
