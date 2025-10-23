# ✅ Setup Checklist

Quick checklist for configuring your RAG bot with mixed Azure OpenAI setup.

## 🎯 Your Configuration Type

You have:
- ✅ Azure OpenAI (direct) with **API key** for LLM
- ✅ Azure APIM with **subscription key** for embeddings

## 📝 Configuration Checklist

### Step 1: Environment File
- [ ] Copy `.env.example` to `.env`
  ```bash
  copy .env.example .env
  ```

### Step 2: Azure OpenAI (LLM) Configuration

- [ ] Get your Azure OpenAI endpoint
  - Format: `https://your-name.openai.azure.com`
  - From: Azure Portal → Azure OpenAI → Keys and Endpoint
  
- [ ] Get your Azure OpenAI API key
  - From: Azure Portal → Azure OpenAI → Keys and Endpoint → KEY 1
  
- [ ] Get your LLM deployment name
  - From: Azure Portal → Azure OpenAI → Model deployments
  - Common names: `gpt-4`, `gpt-35-turbo`

**Add to `.env`:**
```env
AZURE_OPENAI_ENDPOINT=https://your-name.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Step 3: APIM (Embeddings) Configuration

- [ ] Get your APIM endpoint
  - Format: `https://your-apim.azure-api.net`
  - From: Azure Portal → API Management → Overview → Gateway URL
  
- [ ] Get your APIM subscription key
  - From: Azure Portal → API Management → Subscriptions → Show keys
  
- [ ] Get your embedding deployment name
  - Usually: `text-embedding-ada-002` or `text-embedding-3-large`
  - From: Your APIM API configuration

**Add to `.env`:**
```env
AZURE_EMBEDDING_ENDPOINT=https://your-apim.azure-api.net
AZURE_EMBEDDING_KEY=your-subscription-key-here
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_EMBEDDING_API_VERSION=2024-02-15-preview
USE_APIM_FOR_EMBEDDINGS=true
```

### Step 4: Confluence Configuration

- [ ] Get Confluence URL
  - Format: `https://your-domain.atlassian.net`
  
- [ ] Get Confluence username (your email)
  
- [ ] Get Confluence API token
  - Create at: https://id.atlassian.com/manage-profile/security/api-tokens
  
- [ ] Get Confluence space key (optional)
  - From: Confluence → Space Settings → Space Details

**Add to `.env`:**
```env
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-token-here
CONFLUENCE_SPACE_KEY=YOUR_SPACE
```

### Step 5: Jira Configuration

- [ ] Get Jira URL
  - Format: `https://your-domain.atlassian.net`
  - Usually same as Confluence URL
  
- [ ] Get Jira username (your email)
  - Usually same as Confluence username
  
- [ ] Get Jira API token
  - Can use same token as Confluence
  - Or create new at: https://id.atlassian.com/manage-profile/security/api-tokens
  
- [ ] Get Jira project key (optional)
  - From: Jira → Project Settings → Details

**Add to `.env`:**
```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-token-here
JIRA_PROJECT_KEY=YOUR_PROJECT
```

### Step 6: Application Settings (Optional)

These have sensible defaults, but you can customize:

**Add to `.env` (optional):**
```env
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=confluence_jira_docs
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
HYBRID_ALPHA=0.5
API_HOST=0.0.0.0
API_PORT=8000
```

## 🧪 Verification Steps

### 1. Verify Configuration
- [ ] All required fields in `.env` are filled
- [ ] No placeholder text remains (like `your-name-here`)
- [ ] URLs have no trailing slashes
- [ ] Keys are complete (no truncation)

### 2. Test Installation
```bash
# Activate virtual environment
venv\Scripts\activate

# Verify packages installed
pip list | findstr openai
pip list | findstr chromadb
```

### 3. Test Configuration
```bash
# This will test if all connections work
python scripts/index_data.py --source confluence
```

**Expected output:**
```
Initialized Azure OpenAI embeddings via APIM with deployment: text-embedding-ada-002
Fetching Confluence pages...
Fetched X Confluence pages
```

## ⚠️ Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| "Module not found" | `pip install -r requirements.txt` |
| "Azure authentication failed" | Check endpoint format (no `/` at end) |
| "APIM subscription invalid" | Verify key in Azure Portal → APIM → Subscriptions |
| "Confluence 401 error" | Regenerate API token at Atlassian |
| "Deployment not found" | Check deployment name matches Azure exactly |

## 📋 Quick Reference Card

Keep this handy while configuring:

```
┌─────────────────────────────────────────────────────────┐
│ LLM (Azure OpenAI Direct)                               │
├─────────────────────────────────────────────────────────┤
│ Endpoint: https://RESOURCE.openai.azure.com             │
│ Auth: API Key (from Keys and Endpoint)                  │
│ Deployment: gpt-4 or gpt-35-turbo                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Embeddings (APIM)                                       │
├─────────────────────────────────────────────────────────┤
│ Endpoint: https://APIM-NAME.azure-api.net              │
│ Auth: Subscription Key (from Subscriptions)             │
│ Deployment: text-embedding-ada-002                      │
│ Use APIM: true                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Confluence & Jira                                       │
├─────────────────────────────────────────────────────────┤
│ URL: https://YOUR-DOMAIN.atlassian.net                 │
│ Auth: API Token (from id.atlassian.com)                │
│ Username: Your email address                            │
└─────────────────────────────────────────────────────────┘
```

## ✅ Final Checklist

Before running:

- [ ] `.env` file created and configured
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] Azure endpoints tested
- [ ] Confluence/Jira credentials verified

## 🚀 Ready to Go!

Once all checkboxes are complete:

```bash
# Index your data
python scripts/index_data.py --source both

# Start the server
python run.py

# Access the API
# Open: http://localhost:8000/docs
```

---

**Need detailed help?** See `CONFIGURATION_GUIDE.md` for step-by-step instructions.
