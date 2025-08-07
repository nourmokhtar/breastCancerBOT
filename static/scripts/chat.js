// static/scripts/chat.js

async function analyze() {
    const userInput = document.getElementById("userInput").value.trim();
    const textResponse = document.getElementById("textResponse");

    if (!userInput) {
        alert("Please enter a message first.");
        return;
    }

    // Display temporary loading message
    textResponse.innerText = "⏳ Processing...";

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userInput })
        });

        if (!response.ok) {
            throw new Error("Server error: " + response.statusText);
        }

        const data = await response.json();

        // Display assistant's text reply
        textResponse.innerText = data.response || "🤖 No response.";

        // (Optional) Play TTS response here if you add that later

    } catch (err) {
        console.error("❌ Error:", err);
        textResponse.innerText = "❌ An error occurred while contacting the assistant.";
    }
}
