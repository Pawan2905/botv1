# 🚀 Microsoft Teams Deployment Guide

This guide provides a step-by-step process for deploying the RAG bot to Microsoft Teams.

## 📋 Prerequisites

1.  **Microsoft Azure Account**: You will need an Azure account to create and manage the bot.
2.  **ngrok**: A tool that creates a secure tunnel to your local machine, allowing the Microsoft Bot Framework to communicate with your local adapter. [Download ngrok](https://ngrok.com/download).
3.  **Python Environment**: Ensure you have a Python environment with all the necessary dependencies installed.

##  deployment_steps

### Step 1: Register a New Bot in Azure

1.  **Navigate to Azure Portal**: Go to the [Azure Portal](https://portal.azure.com/).
2.  **Create a Resource**: Search for "Azure Bot" and create a new bot resource.
3.  **Configuration**:
    *   **Bot handle**: A unique name for your bot.
    *   **Subscription**: Your Azure subscription.
    *   **Resource group**: Create a new one or use an existing one.
    *   **Pricing tier**: The Free (F0) tier is sufficient for testing.
    *   **Type of App**: Select "Multi Tenant".
4.  **Get Credentials**: Once the bot is created, go to the **Configuration** page and note down the following values. You will need them later:
    *   **Microsoft App ID**
    *   **Microsoft App Password** (you may need to generate a new client secret for this)

### Step 2: Configure and Run the Bot Locally

1.  **Set Environment Variables**: Before running the applications, you need to set the following environment variables:
    *   `MicrosoftAppId`: The App ID you got from the Azure portal.
    *   `MicrosoftAppPassword`: The App Password you got from the Azure portal.
    *   `RagBotApiUrl`: The URL of your RAG bot's chat endpoint (e.g., `http://localhost:8000/chat`).

2.  **Run the RAG Bot**: Open a terminal and start the main RAG bot application:
    ```bash
    python run.py
    ```
    This will start the bot on `http://localhost:8000`.

3.  **Run the Teams Adapter**: Open a *second* terminal and start the Teams adapter:
    ```bash
    python teams_adapter.py
    ```
    This will start the adapter on `http://localhost:3978`.

### Step 3: Expose Your Local Adapter with ngrok

1.  **Start ngrok**: In a *third* terminal, run the following command to create a secure tunnel to your Teams adapter:
    ```bash
    ngrok http 3978
    ```
2.  **Get the Forwarding URL**: ngrok will provide you with a public HTTPS URL (e.g., `https://<random-string>.ngrok.io`). Copy this URL.

### Step 4: Configure the Bot's Messaging Endpoint

1.  **Return to Azure Portal**: Go back to your Azure Bot's **Configuration** page.
2.  **Set the Messaging Endpoint**: In the "Messaging endpoint" field, paste the ngrok URL you copied and append `/api/messages`. The final URL should look like this:
    ```
    https://<random-string>.ngrok.io/api/messages
    ```
3.  **Save** your changes.

### Step 5: Add the Teams Channel and Test

1.  **Add the Teams Channel**: In your Azure Bot's settings, go to the **Channels** page and add the "Microsoft Teams" channel.
2.  **Test in Teams**:
    *   On the Channels page, click the "Open in Teams" link.
    *   This will open a chat with your bot in Microsoft Teams.
    *   Send a message to the bot. It should now be fully operational and connected to your local RAG bot.

## 🚀 Going to Production

When you are ready to move to a production environment, you will need to:

1.  **Deploy the RAG Bot and Teams Adapter**: Host both the `run.py` and `teams_adapter.py` applications on a cloud service like Azure App Service or a virtual machine.
2.  **Update the Messaging Endpoint**: In the Azure portal, update the messaging endpoint to point to your deployed Teams adapter's public URL.
3.  **Secure Your Credentials**: Use a secure method like Azure Key Vault to store your App ID and App Password instead of environment variables.

This guide should provide everything you need to get your bot up and running in Microsoft Teams.
