# Configuration Guide for Mixed Azure OpenAI Setup

This guide helps you configure the system when you have:
- **Azure OpenAI (direct)** for LLM with API key
- **Azure API Management (APIM)** for embeddings with subscription key

## 📋 What You Need

### 1. Azure OpenAI (Direct) - For LLM
- **Endpoint**: Your Azure OpenAI resource endpoint
  - Format: `https://your-resource-name.openai.azure.com`
  - Example: `https://mycompany-openai.openai.azure.com`
- **API Key**: Found in Azure Portal → Azure OpenAI → Keys and Endpoint
- **Deployment Name**: Your GPT model deployment name (e.g., `gpt-4`, `gpt-35-turbo`)

### 2. Azure API Management (APIM) - For Embeddings
- **Endpoint**: Your APIM gateway URL
  - Format: `https://your-apim-name.azure-api.net`
  - Example: `https://mycompany-apim.azure-api.net`
- **Subscription Key**: Found in Azure Portal → API Management → Subscriptions
- **Deployment Name**: Your embedding model deployment name (e.g., `text-embedding-ada-002`)

## ⚙️ Step-by-Step Configuration

### Step 1: Copy the Example File

```bash
copy .env.example .env
```

### Step 2: Configure Azure OpenAI (LLM)

Edit your `.env` file and fill in these values:

```env
# Azure OpenAI Configuration (LLM - Direct Access)
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_KEY=your-32-character-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**How to get these values:**

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your **Azure OpenAI** resource
3. Click **Keys and Endpoint** (left menu)
4. Copy:
   - **Endpoint** → `AZURE_OPENAI_ENDPOINT`
   - **KEY 1** or **KEY 2** → `AZURE_OPENAI_API_KEY`
5. Go to **Model deployments** → **Manage Deployments**
6. Copy your LLM deployment name → `AZURE_OPENAI_DEPLOYMENT_NAME`

### Step 3: Configure APIM (Embeddings)

```env
# Azure OpenAI Embeddings Configuration (APIM)
AZURE_EMBEDDING_ENDPOINT=https://your-apim-name.azure-api.net
AZURE_EMBEDDING_KEY=your-apim-subscription-key-here
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_EMBEDDING_API_VERSION=2024-02-15-preview
USE_APIM_FOR_EMBEDDINGS=true
```

**How to get these values:**

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your **API Management** service
3. Click **Subscriptions** (left menu)
4. Find your subscription and click **Show/hide keys**
5. Copy:
   - **Gateway URL** → `AZURE_EMBEDDING_ENDPOINT`
   - **Primary key** or **Secondary key** → `AZURE_EMBEDDING_KEY`
6. The deployment name should match your embedding model deployment

### Step 4: Configure Confluence and Jira

```env
# Confluence Configuration
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_SPACE_KEY=YOUR_SPACE

# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=YOUR_PROJECT
```

**How to get Atlassian API tokens:**

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g., "RAG Bot")
4. Copy the token immediately (you won't see it again!)
5. Use the same token for both Confluence and Jira

## 📝 Complete Example `.env` File

```env
# Azure OpenAI Configuration (LLM - Direct Access)
AZURE_OPENAI_ENDPOINT=https://mycompany-openai.openai.azure.com
AZURE_OPENAI_API_KEY=abcd1234efgh5678ijkl9012mnop3456
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure OpenAI Embeddings Configuration (APIM)
AZURE_EMBEDDING_ENDPOINT=https://mycompany-apim.azure-api.net
AZURE_EMBEDDING_KEY=9876543210abcdefghijklmnopqrstuv
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_EMBEDDING_API_VERSION=2024-02-15-preview
USE_APIM_FOR_EMBEDDINGS=true

# Confluence Configuration
CONFLUENCE_URL=https://mycompany.atlassian.net
CONFLUENCE_USERNAME=bot@mycompany.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0Q1...rest_of_token
CONFLUENCE_SPACE_KEY=ENG

# Jira Configuration
JIRA_URL=https://mycompany.atlassian.net
JIRA_USERNAME=bot@mycompany.com
JIRA_API_TOKEN=ATATT3xFfGF0Q1...rest_of_token
JIRA_PROJECT_KEY=PROJ

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=confluence_jira_docs

# Application Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
HYBRID_ALPHA=0.5

# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## 🔍 Verification

### Test Your Configuration

```bash
# Activate virtual environment
venv\Scripts\activate

# Test by starting the indexing process (it will fail quickly if config is wrong)
python scripts/index_data.py --source confluence
```

### Expected Success Messages

If configured correctly, you should see:
```
Initialized Azure OpenAI embeddings via APIM with deployment: text-embedding-ada-002
Initializing components...
Fetching Confluence pages...
```

### Common Configuration Errors

#### Error: "Azure OpenAI authentication failed"
**Cause**: Wrong API key or endpoint
**Solution**: 
- Verify endpoint format: `https://resource-name.openai.azure.com` (no trailing slash)
- Regenerate API key in Azure Portal and update `.env`

#### Error: "APIM subscription key invalid"
**Cause**: Wrong subscription key or endpoint
**Solution**:
- Verify APIM endpoint: `https://apim-name.azure-api.net` (no trailing slash)
- Check subscription is active in Azure Portal
- Try the secondary key if primary doesn't work

#### Error: "Deployment not found"
**Cause**: Deployment name doesn't match Azure
**Solution**:
- Go to Azure Portal → OpenAI → Model deployments
- Copy the exact deployment name (case-sensitive)

#### Error: "Confluence authentication failed"
**Cause**: Invalid API token or URL
**Solution**:
- Test URL in browser: `https://your-domain.atlassian.net`
- Regenerate API token at [Atlassian Security](https://id.atlassian.com/manage-profile/security/api-tokens)
- Ensure email matches your Atlassian account

## 🔒 Security Best Practices

1. **Never commit `.env` file**
   - Already in `.gitignore`
   - Keep credentials secure

2. **Use separate service accounts**
   - Create dedicated accounts for bot access
   - Use minimal required permissions

3. **Rotate keys regularly**
   - Azure: Regenerate keys every 90 days
   - Atlassian: Regenerate tokens every 6 months

4. **Monitor usage**
   - Check Azure costs regularly
   - Review API usage in Azure Monitor

## 🚀 Next Steps

After configuration:

1. **Test the setup**:
   ```bash
   python scripts/index_data.py --source both
   ```

2. **Start the server**:
   ```bash
   python run.py
   ```

3. **Access the API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

## 🆘 Still Having Issues?

### Check Configuration Values
```python
# Quick test script
from config import settings

print("LLM Endpoint:", settings.azure_openai_endpoint)
print("Embedding Endpoint:", settings.azure_embedding_endpoint)
print("Using APIM:", settings.use_apim_for_embeddings)
print("Confluence URL:", settings.confluence_url)
print("Jira URL:", settings.jira_url)
```

### Enable Debug Logging
Edit `run.py` or any script and change:
```python
logging.basicConfig(level=logging.DEBUG)  # Changed from INFO
```

### Test Components Individually

**Test Azure OpenAI (LLM)**:
```python
from openai import AzureOpenAI
from config import settings

client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version
)

response = client.chat.completions.create(
    model=settings.azure_openai_deployment_name,
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

**Test APIM (Embeddings)**:
```python
from storage.embeddings import AzureOpenAIEmbeddings
from config import settings

embeddings = AzureOpenAIEmbeddings(
    endpoint=settings.azure_embedding_endpoint,
    api_key=settings.azure_embedding_key,
    deployment_name=settings.azure_embedding_deployment,
    api_version=settings.azure_embedding_api_version,
    use_apim=True
)

result = embeddings.embed_query("test")
print(f"Embedding dimension: {len(result)}")
```

---

**Need more help?** Check the README.md for detailed documentation.
