// --- Shared Utilities ---

const API_BASE_URL = "http://127.0.0.1:8000";

/** Cache DOM elements once to avoid repeated lookups on every event. */
const elements = {
    canvas: document.getElementById("sketchCanvas"),
    brushSize: document.getElementById("brushSize"),
    colorPicker: document.getElementById("colorPicker"),
    promptInput: document.getElementById("promptInput"),
    generateBtn: document.getElementById("generateBtn"),
    loadingText: document.getElementById("loadingText"),
    resultImage: document.getElementById("resultImage"),
};

const ctx = elements.canvas.getContext("2d");

/**
 * Reset the canvas to a blank white state.
 * Reused during initialization and when the user clicks "Hapus Kanvas".
 */
function resetCanvas() {
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, elements.canvas.width, elements.canvas.height);
}

/**
 * Toggle the UI between loading and idle states.
 * Eliminates duplication of enabling/disabling controls in multiple places.
 *
 * @param {boolean} isLoading - Whether the app is currently generating.
 */
function setLoadingState(isLoading) {
    elements.generateBtn.disabled = isLoading;
    elements.loadingText.style.display = isLoading ? "block" : "none";
    if (isLoading) {
        elements.resultImage.style.display = "none";
    }
}

// --- Canvas Drawing Logic ---

let isDrawing = false;

function startDrawing(e) {
    isDrawing = true;
    draw(e);
}

function draw(e) {
    if (!isDrawing) return;

    const rect = elements.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineWidth = elements.brushSize.value;
    ctx.lineCap = "round";
    ctx.strokeStyle = elements.colorPicker.value;

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
}

function stopDrawing() {
    isDrawing = false;
    ctx.beginPath();
}

// --- Event Listeners ---

elements.canvas.addEventListener("mousedown", startDrawing);
elements.canvas.addEventListener("mousemove", draw);
elements.canvas.addEventListener("mouseup", stopDrawing);
elements.canvas.addEventListener("mouseout", stopDrawing);

// --- Public Actions ---

function clearCanvas() {
    resetCanvas();
    elements.resultImage.style.display = "none";
}

async function generateImage() {
    const prompt = elements.promptInput.value;

    if (!prompt) {
        alert("Masukkan instruksi prompt terlebih dahulu!");
        return;
    }

    const base64Image = elements.canvas.toDataURL("image/png");

    setLoadingState(true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/generate-from-sketch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: base64Image, prompt: prompt }),
        });

        if (!response.ok) {
            throw new Error("Gagal mengambil respons dari server");
        }

        const data = await response.json();

        if (data.status === "success") {
            elements.resultImage.src = data.generated_image;
            elements.resultImage.style.display = "block";
        }
    } catch (error) {
        console.error("Error:", error);
        alert("Terjadi kesalahan! Pastikan server FastAPI sedang berjalan.");
    } finally {
        setLoadingState(false);
    }
}

// --- Initialization ---
resetCanvas();
