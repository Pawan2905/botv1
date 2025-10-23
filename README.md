# Confluence & Jira RAG Bot

A production-ready AI-powered bot that fetches, indexes, and queries data from Confluence and Jira using hybrid retrieval (dense vector search + sparse BM25) with Azure OpenAI.

## 🚀 Features

- **Multi-Source Data Fetching**: Fetch documents from Confluence and Jira
- **Intelligent Chunking**: Automatically chunk documents with overlap for better context
- **Hybrid Retrieval**: Combines dense (vector similarity) and sparse (BM25) search using Reciprocal Rank Fusion
- **Azure OpenAI Integration**: Use Azure OpenAI for embeddings and chat completions
- **ChromaDB Storage**: Persistent vector database with metadata filtering
- **FastAPI Backend**: Production-ready REST API with automatic documentation
- **Jira Operations**: Create, update, and manage Jira issues directly from the bot
- **MCP Server**: Model Context Protocol server for efficient multi-source integration
- **Live Jira Fetching**: Option to fetch live Jira data for real-time queries

## 📁 Project Structure

```
botv1/
├── api/                      # FastAPI application
│   ├── __init__.py
│   ├── main.py              # FastAPI routes and app
│   ├── models.py            # Pydantic models
│   └── bot_service.py       # Main bot service logic
├── data_fetchers/           # Data source fetchers
│   ├── __init__.py
│   ├── confluence_fetcher.py
│   └── jira_fetcher.py
├── storage/                 # Storage and embeddings
│   ├── __init__.py
│   ├── chroma_store.py      # ChromaDB integration
│   ├── embeddings.py        # Azure OpenAI embeddings
│   └── chunker.py           # Text chunking logic
├── retrieval/               # Retrieval systems
│   ├── __init__.py
│   ├── hybrid_retriever.py  # Hybrid search (RRF)
│   └── bm25_retriever.py    # BM25 sparse retrieval
├── mcp_server/              # MCP integration
│   ├── __init__.py
│   └── mcp_integration.py   # Multi-source protocol server
├── scripts/                 # Utility scripts
│   ├── index_data.py        # Index data from sources
│   └── test_retrieval.py    # Test retrieval system
├── config.py                # Configuration management
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🛠️ Installation

### 1. Clone or Download the Project

```bash
cd e:\UV_Demo\botv1
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
copy .env.example .env  # Windows
# or
cp .env.example .env    # Linux/Mac
```

Edit `.env` with your actual credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-apim-endpoint.azure-api.net
AZURE_OPENAI_API_KEY=your-subscription-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-15-preview

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

## 📊 Usage

### Step 1: Index Data

Index data from Confluence and/or Jira into ChromaDB:

```bash
# Index both Confluence and Jira
python scripts/index_data.py --source both

# Index only Confluence
python scripts/index_data.py --source confluence

# Index only Jira
python scripts/index_data.py --source jira

# Refresh (delete existing data and re-index)
python scripts/index_data.py --source both --refresh

# Use MCP server for multi-source integration
python scripts/index_data.py --source both --use-mcp
```

### Step 2: Test Retrieval

Test the hybrid retrieval system:

```bash
python scripts/test_retrieval.py
```

### Step 3: Start the API Server

```bash
python -m api.main

# Or with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## 🔌 API Endpoints

### Health Check
```http
GET /health
```

### Index Data
```http
POST /index
Content-Type: application/json

{
  "source": "both",  // "confluence", "jira", or "both"
  "refresh": false
}
```

### Query Knowledge Base
```http
POST /query
Content-Type: application/json

{
  "query": "How do I configure authentication?",
  "top_k": 5,
  "method": "hybrid",  // "hybrid", "dense", or "sparse"
  "filters": {"doc_type": "confluence"}  // optional
}
```

### Chat with Bot
```http
POST /chat
Content-Type: application/json

{
  "message": "What are the latest bugs?",
  "conversation_history": [],
  "top_k": 5,
  "use_jira_live": false
}
```

### Create Jira Issue
```http
POST /jira/issue
Content-Type: application/json

{
  "project_key": "PROJ",
  "summary": "New feature request",
  "description": "Detailed description here",
  "issue_type": "Task",
  "priority": "High",
  "labels": ["feature", "enhancement"]
}
```

### Update Jira Issue
```http
PUT /jira/issue/{issue_key}
Content-Type: application/json

{
  "summary": "Updated summary",
  "status": "In Progress",
  "priority": "Critical"
}
```

### Add Comment to Jira Issue
```http
POST /jira/issue/{issue_key}/comment
Content-Type: application/json

{
  "comment": "This is a comment"
}
```

### Get Jira Issue
```http
GET /jira/issue/{issue_key}
```

### Search Jira Issues
```http
GET /jira/search?query=authentication&max_results=20
```

## 🔍 Hybrid Retrieval Explained

The system uses **Reciprocal Rank Fusion (RRF)** to combine:

1. **Dense Retrieval**: Vector similarity using Azure OpenAI embeddings
2. **Sparse Retrieval**: Keyword matching using BM25 algorithm

### RRF Formula:
```
RRF_score = α × (1 / (k + dense_rank)) + (1 - α) × (1 / (k + sparse_rank))
```

Where:
- `α` (alpha): Weight between dense and sparse (default: 0.5)
- `k`: RRF constant (default: 60)
- Higher `α` → More weight on semantic similarity
- Lower `α` → More weight on keyword matching

### Configuration

Adjust in `.env`:
```env
HYBRID_ALPHA=0.5  # 0.0 = full BM25, 1.0 = full dense
```

## 🔧 Configuration Parameters

### Chunking
```env
CHUNK_SIZE=1000          # Characters per chunk
CHUNK_OVERLAP=200        # Overlapping characters
```

### Retrieval
```env
TOP_K_RESULTS=5          # Default number of results
HYBRID_ALPHA=0.5         # Hybrid retrieval weight
```

### ChromaDB
```env
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=confluence_jira_docs
```

## 🧪 Testing Examples

### Python Client Example

```python
import requests

# Query the knowledge base
response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "How to configure SSO?",
        "top_k": 5,
        "method": "hybrid"
    }
)
print(response.json())

# Chat with the bot
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "Show me recent bugs in authentication",
        "use_jira_live": True
    }
)
print(response.json()["response"])

# Create a Jira issue
response = requests.post(
    "http://localhost:8000/jira/issue",
    json={
        "project_key": "PROJ",
        "summary": "Implement new authentication method",
        "description": "Based on the documentation review",
        "issue_type": "Task"
    }
)
print(response.json())
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "API documentation", "top_k": 3, "method": "hybrid"}'

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the open issues?", "use_jira_live": true}'
```

## 🎯 Best Practices

### 1. **Indexing Strategy**
- Index during off-peak hours for large datasets
- Use `--refresh` flag sparingly (deletes all existing data)
- Consider incremental updates for production

### 2. **Retrieval Method Selection**
- **Hybrid**: Best for most use cases (balanced)
- **Dense**: Better for semantic/conceptual queries
- **Sparse**: Better for exact keyword matches

### 3. **Rate Limiting**
- Azure OpenAI has rate limits
- Adjust batch sizes in `embeddings.py` if needed
- Consider implementing caching for frequent queries

### 4. **Security**
- Never commit `.env` file with real credentials
- Use Azure Key Vault for production secrets
- Implement authentication on FastAPI endpoints

### 5. **Performance Optimization**
- Increase `chunk_size` for longer documents
- Reduce `top_k` for faster responses
- Use filters to narrow search scope

## 🔐 Security Notes

1. **API Tokens**: Store securely in `.env` (never commit)
2. **API Authentication**: Add authentication middleware to FastAPI
3. **CORS**: Configure allowed origins in production
4. **Rate Limiting**: Implement rate limiting for public APIs
5. **Input Validation**: Already implemented via Pydantic models

## 🐛 Troubleshooting

### Issue: "ChromaDB collection not found"
**Solution**: Run the indexing script first:
```bash
python scripts/index_data.py --source both
```

### Issue: "Azure OpenAI authentication failed"
**Solution**: Check your `.env` file for correct:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`

### Issue: "Confluence/Jira connection failed"
**Solution**: 
1. Verify API tokens are valid
2. Check network connectivity
3. Ensure URLs are correct (include `https://`)

### Issue: "No results returned"
**Solution**:
1. Ensure data is indexed
2. Try different retrieval methods
3. Check filters aren't too restrictive

## 📈 Monitoring and Logging

Logs are configured with timestamps and levels:
- **INFO**: Normal operations
- **WARNING**: Potential issues
- **ERROR**: Failures and exceptions

View logs in console or redirect to file:
```bash
python -m api.main > app.log 2>&1
```

## 🚀 Production Deployment

### Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t rag-bot .
docker run -p 8000:8000 --env-file .env rag-bot
```

### Environment Variables for Production
- Use Azure Key Vault or AWS Secrets Manager
- Set `API_HOST=0.0.0.0`
- Configure proper logging levels

## 📚 Advanced Features

### MCP Server Integration

The MCP (Model Context Protocol) server provides efficient multi-source data integration:

```python
from mcp_server import MCPServer

# Initialize MCP server
mcp = MCPServer()

# Register sources
mcp.register_data_source("confluence", "confluence", confluence_fetcher)
mcp.register_data_source("jira", "jira", jira_fetcher)

# Fetch from all sources
results = mcp.fetch_from_all_sources(query="authentication")

# Aggregate results
aggregated = mcp.aggregate_results(results, merge_strategy="deduplicate")
```

### Custom Filters

Apply metadata filters to narrow search:

```python
# Query only Confluence pages from specific space
filters = {"space": "ENGINEERING", "doc_type": "confluence"}

response = requests.post(
    "http://localhost:8000/query",
    json={"query": "API docs", "filters": filters}
)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is provided as-is for educational and commercial use.

## 🙋 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Check logs for detailed error messages

## 🎉 Acknowledgments

- **Azure OpenAI** for embeddings and LLM
- **ChromaDB** for vector storage
- **FastAPI** for the web framework
- **Atlassian** for Confluence and Jira APIs

---

**Built with ❤️ for efficient knowledge management and retrieval**
