const API_URL = "http://127.0.0.1:5000/predict";

const dropZone    = document.getElementById("drop-zone");
const dropContent = document.getElementById("drop-content");
const fileInput   = document.getElementById("file-input");
const preview     = document.getElementById("preview");
const resultBox   = document.getElementById("result-box");
const resultLabel = document.getElementById("result-label");
const resultConf  = document.getElementById("result-confidence");
const resultBar   = document.getElementById("result-bar");
const errorBox    = document.getElementById("error-box");
const loading     = document.getElementById("loading");
const resetBtn    = document.getElementById("reset-btn");
const correctBtn  = document.getElementById("correct-btn");
const wrongBtn    = document.getElementById("wrong-btn");
const feedback = document.getElementById("feedback-txt");

// Drag & drop events
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) handleImage(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) handleImage(file);
});

resetBtn.addEventListener("click", () => {
  resultBox.style.display = "none";
  resultBox.className = "";
  errorBox.style.display = "none";
  preview.style.display = "none";
  dropContent.style.display = "flex";
  fileInput.value = "";
  hideButtons();
  feedback.style.display = "none";
});

correctBtn.addEventListener("click", () => {
  feedbackText();
})

wrongBtn.addEventListener("click", () => {
  feedbackText();
})

function hideButtons(){
  resetBtn.style.display = "none";
  correctBtn.style.display = "none";
  wrongBtn.style.display = "none";
}

function feedbackText(){
  feedback.style.display = "block";
  hideButtons();
  resetBtn.style.display = "block";
}

function handleImage(file) {
  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    preview.src = e.target.result;
    preview.style.display = "block";
    dropContent.style.display = "none";
  };
  reader.readAsDataURL(file);

  // Send to API
  sendToAPI(file);
}

async function sendToAPI(file) {
  resultBox.style.display = "none";
  errorBox.style.display = "none";
  loading.style.display = "block";
  hideButtons();

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.error) throw new Error(data.error);

    // Show result
    resultBox.style.display = "block";
    resultBox.className = data.label;  // "REAL" or "FAKE"

    const emoji = data.label === "FAKE" ? "🚨 FAKE" : "✅ REAL";
    resultLabel.textContent = emoji;
    resultConf.textContent = `Confidence: ${data.confidence}%`;
    resultBar.style.width = `${data.confidence}%`;

  } catch (err) {
    errorBox.style.display = "block";
    errorBox.textContent = `⚠️ Error: ${err.message}. Is the API running on localhost:5000?`;
  } finally {
    loading.style.display = "none";
    resetBtn.style.display = "block";
    wrongBtn.style.display = "inline-block";
    correctBtn.style.display = "inline-block";
  }
}