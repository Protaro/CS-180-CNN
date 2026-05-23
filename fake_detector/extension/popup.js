const API_URL = "http://127.0.0.1:5000";

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

let currentImage = "";
let UIState = "IDLE";
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
  fileInput.value = "";
  setIdle();
});

correctBtn.addEventListener("click", async () => {
  await sendFeedback(true);
  setFeedback();
})

wrongBtn.addEventListener("click", async () => {
  await sendFeedback(false);
  setFeedback();
})

function render() {
  resultBox.style.display = "none";
  errorBox.style.display = "none";
  loading.style.display = "none";

  resetBtn.style.display = "none";
  correctBtn.style.display = "none";
  wrongBtn.style.display = "none";
  feedback.style.display = "none";

  if (UIState === "IDLE") {
    preview.style.display = "none";
    dropContent.style.display = "flex";
    return;
  }
  preview.style.display = "block";
  dropContent.style.display = "none";

  if (UIState === "LOADING") {
    loading.style.display = "block";
  }

  if (UIState === "PREDICTION") {
    resultBox.style.display = "block";
    resetBtn.style.display = "block";
    correctBtn.style.display = "inline-block";
    wrongBtn.style.display = "inline-block";
  }

  if (UIState === "FEEDBACK") {
    feedback.style.display = "block";
    resetBtn.style.display = "block";
  }
}

function setIdle(){
  UIState = "IDLE";
  render();
}

function setPrediction(data) {
  UIState = "PREDICTION";
  resultBox.className = data.label;
  const emoji = data.label === "FAKE" ? "🚨 FAKE" : "✅ REAL";
  resultLabel.textContent = emoji;
  resultConf.textContent = `Confidence: ${data.confidence}%`;
  resultBar.style.width = `${data.confidence}%`;
  render();
}

function setFeedback() {
  UIState = "FEEDBACK";
  render();
}

async function sendFeedback(isCorrect) {
  const formData = new FormData();
  formData.append("image", currentImage);
  formData.append("accurate", isCorrect ? "true" : "false");
  formData.append("result", resultBox.className);
  formData.append("confidence", resultBar.style.width);

  try {
    await fetch(`${API_URL}/feedback`, {
      method: "POST",
      body: formData
    });
  } catch (err) {
    console.error(err);
  }
}

function handleImage(file) {
  setIdle();
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
  currentImage = file;
  UIState = "LOADING";
  render();

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch(`${API_URL}/predict`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    if (data.error) throw new Error(data.error);
    setPrediction(data);
  } catch (err) {
    UIState = "IDLE";
    errorBox.style.display = "block";
    errorBox.textContent = `⚠️ Error: ${err.message}. Is the API running on localhost:5000?`;
    render();
  } 
}