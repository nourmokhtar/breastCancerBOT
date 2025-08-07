let mediaRecorder;
let audioChunks = [];

async function startVoice() {
    console.log("🎙️ Starting audio recording...");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append("file", audioBlob, "voice_input.wav");

            try {
                const res = await fetch("/analyze_voice", {
                    method: "POST",
                    body: formData
                });

                const result = await res.json();
                console.log("🎯 Voice Emotion Result:", result);

                if (result.error) {
                    console.error("⚠️ Server Error:", result.error);
                    alert("Server error: " + result.error);
                    return;
                }

                // 🧠 Update UI with results
                if (result.transcription) {
                    document.getElementById("userInput").value = result.transcription;
                }

                if (result.emotion) {
                    document.getElementById("emotions").innerText =
                        `🎤 Detected voice emotion: ${result.emotion} (${result.confidence}%)`;
                }

                // Affichage LLM textuel
                if (result.response) {
                    document.getElementById("textResponse").innerText = result.response;
                }

                // 🔊 Play LLM audio response if available with cache busting
                if (result.audio_url) {
                    const audioPlayer = document.getElementById("responseAudio");
                    // Add timestamp query param to force reload
                    audioPlayer.src = result.audio_url + "?t=" + Date.now();
                    audioPlayer.style.display = "block";
                    audioPlayer.play().catch(err => {
                        console.error("🔇 Audio playback error:", err);
                    });
                }

            } catch (err) {
                console.error("❌ Error uploading audio:", err);
                alert("Failed to analyze voice. See console for details.");
            }
        };

        mediaRecorder.start();
        console.log("🔴 Recording...");
    } catch (err) {
        console.error("🎤 Microphone access denied or unavailable:", err);
        alert("Microphone access is required for voice input.");
    }
}

function stopVoice() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        console.log("🛑 Recording stopped.");
    }
}
