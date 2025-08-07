async function analyze() {
    const text = document.getElementById("userInput").value;
    if (!text.trim()) {
        alert("Please enter how you feel.");
        return;
    }

    try {
        const res = await fetch("/analyze", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await res.json();
        document.getElementById("emotions").innerText = JSON.stringify(data.emotions, null, 2);
        document.getElementById("response").innerText = data.response || "⚠️ No LLM response received.";
    } catch (error) {
        console.error("Error analyzing text:", error);
        document.getElementById("response").innerText = "⚠️ Error analyzing text.";
    }
}
