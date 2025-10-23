# 🚀 Quick Start Guide

Get up and running with the Confluence & Jira RAG Bot in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- Azure OpenAI API access with APIM endpoint
- Confluence and Jira access with API tokens

## Step 1: Install Dependencies (2 minutes)

```bash
# Navigate to project directory
cd e:\UV_Demo\botv1

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment (1 minute)

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` and add your credentials:
```env
# Azure OpenAI (REQUIRED)
AZURE_OPENAI_ENDPOINT=https://your-apim.azure-api.net
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Confluence (REQUIRED)
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-token-here
CONFLUENCE_SPACE_KEY=YOUR_SPACE

# Jira (REQUIRED)
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-token-here
JIRA_PROJECT_KEY=YOUR_PROJECT
```

### How to Get API Tokens:

**Confluence/Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name and copy the token

**Azure OpenAI:**
1. Get endpoint from Azure Portal (API Management service)
2. Get subscription key from APIM → Subscriptions

## Step 3: Index Your Data (Variable time)

```bash
# Index both Confluence and Jira
python scripts/index_data.py --source both

# This will:
# - Fetch all pages from Confluence
# - Fetch all issues from Jira
# - Chunk the documents
# - Generate embeddings
# - Store in ChromaDB
```

**Expected output:**
```
Starting data indexing process
Fetching Confluence pages...
Fetched 50 Confluence pages
Fetching Jira issues...
Fetched 100 Jira issues
Chunking documents...
Created 450 chunks
Generating embeddings...
Generated 450 embeddings
Adding documents to ChromaDB...
Indexing completed successfully!
```

## Step 4: Start the API Server

```bash
python run.py
```

**Server will start at:** http://localhost:8000

**API Documentation:** http://localhost:8000/docs

## Step 5: Test the Bot! 🎉

### Option A: Use the Interactive API Docs

1. Open http://localhost:8000/docs in your browser
2. Try the `/chat` endpoint
3. Click "Try it out"
4. Enter a message like "What are the latest bugs?"
5. Click "Execute"

### Option B: Use cURL

```bash
# Health check
curl http://localhost:8000/health

# Query the knowledge base
curl -X POST http://localhost:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"How to configure authentication?\", \"top_k\": 5, \"method\": \"hybrid\"}"

# Chat with the bot
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What are the open issues in the project?\"}"
```

### Option C: Use Python

```python
import requests

# Chat with the bot
response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "Show me documentation about API endpoints"}
)

print(response.json()["response"])
print("\nSources:")
for source in response.json()["sources"]:
    print(f"- {source['title']} ({source['type']})")
```

## Common First-Time Issues

### Issue: "ModuleNotFoundError"
```bash
# Make sure virtual environment is activated
venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: "Connection refused" from Confluence/Jira
- Check your URL format: `https://your-domain.atlassian.net`
- Verify API token is correct
- Test credentials at: https://your-domain.atlassian.net/wiki

### Issue: "Azure OpenAI authentication failed"
- Verify endpoint URL (should include `https://`)
- Check API key is correct
- Ensure deployment names match your Azure setup

### Issue: "No documents found in ChromaDB"
- Run the indexing script first: `python scripts/index_data.py --source both`
- Wait for indexing to complete

## What's Next?

### Test Different Retrieval Methods

```python
import requests

query = "authentication documentation"

# Hybrid (best for most cases)
response = requests.post(
    "http://localhost:8000/query",
    json={"query": query, "method": "hybrid"}
)

# Dense (semantic search)
response = requests.post(
    "http://localhost:8000/query",
    json={"query": query, "method": "dense"}
)

# Sparse (keyword search)
response = requests.post(
    "http://localhost:8000/query",
    json={"query": query, "method": "sparse"}
)
```

### Create Jira Issues from the Bot

```python
import requests

response = requests.post(
    "http://localhost:8000/jira/issue",
    json={
        "project_key": "PROJ",
        "summary": "Implement new feature",
        "description": "Based on team discussion",
        "issue_type": "Task",
        "priority": "High"
    }
)

print(f"Created issue: {response.json()['key']}")
```

### Use Live Jira Data

```python
import requests

# Bot will fetch live Jira issues matching the query
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "Show me high priority bugs",
        "use_jira_live": True
    }
)

print(response.json()["response"])
```

## Performance Tips

1. **Faster Indexing**: Reduce `CHUNK_SIZE` for quicker processing
2. **Better Accuracy**: Increase `TOP_K_RESULTS` for more context
3. **Semantic vs Keywords**: Adjust `HYBRID_ALPHA` (0.5 is balanced)

## Need Help?

- Check the full README.md for detailed documentation
- Visit http://localhost:8000/docs for API reference
- Review logs for error messages
- Run test script: `python scripts/test_retrieval.py`

---

**You're all set! Happy querying! 🎉**
