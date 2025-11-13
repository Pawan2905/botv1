document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");

    let conversationHistory = [];

    const addMessage = (message, sender) => {
        const messageElement = document.createElement("div");
        messageElement.classList.add("chat-message", `${sender}-message`);

        const bubble = document.createElement("div");
        bubble.classList.add("message-bubble");
        bubble.textContent = message;

        messageElement.appendChild(bubble);
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    };

    const sendMessage = async () => {
        const message = userInput.value.trim();
        if (message === "") return;

        addMessage(message, "user");
        userInput.value = "";

        conversationHistory.push({ role: "user", content: message });

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query: message,
                    conversation_history: conversationHistory,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const botMessage = data.response;

            addMessage(botMessage, "bot");
            conversationHistory.push({ role: "assistant", content: botMessage });

        } catch (error) {
            console.error("Error fetching chat response:", error);
            addMessage("Sorry, something went wrong. Please try again.", "bot");
        }
    };

    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    // Initial bot message
    addMessage("Hello! How can I help you today?", "bot");
});
