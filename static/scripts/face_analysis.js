const canvas = document.getElementById("canvas");
const context = canvas.getContext("2d");

function captureFrame() {
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg");
}

async function sendFrame() {
    if (!videoElement || videoElement.readyState !== 4) return;

    const imageData = captureFrame();

    try {
        const response = await fetch("/analyze_frame", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: imageData })
        });

        const result = await response.json();
        console.log("🎯 Emotion result:", result);

        if (result.emotion) {
            document.getElementById("emotions").innerText = `${result.emotion} (${result.confidence}%)`;
        } else {
            document.getElementById("emotions").innerText = "⚠️ Unable to detect emotion.";
        }
    } catch (error) {
        console.error("❌ Error sending frame:", error);
    }
}

// Send frame every 10 seconds
setInterval(sendFrame, 10000);
