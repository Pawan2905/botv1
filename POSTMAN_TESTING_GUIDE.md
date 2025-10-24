# 🚀 Postman Testing Guide

Complete guide to test the Confluence & Jira RAG Bot API using Postman.

## 📋 Prerequisites

1. ✅ Server is running
   ```bash
   python run.py
   ```
   Server should be at: `http://localhost:8000`

2. ✅ Data is indexed
   ```bash
   python scripts/index_data.py --source both
   ```

3. ✅ Postman installed
   - Download from: https://www.postman.com/downloads/

## 🎯 Quick Setup

### Base URL
```
http://localhost:8000
```

### Headers (for all POST/PUT requests)
```
Content-Type: application/json
```

---

## 📡 API Endpoints to Test

### 1. Health Check ✅

**Purpose:** Verify the server is running and check system stats

**Request:**
- **Method:** `GET`
- **URL:** `http://localhost:8000/health`
- **Headers:** None needed

**Postman Steps:**
1. Create new request
2. Set method to `GET`
3. Enter URL: `http://localhost:8000/health`
4. Click **Send**

**Expected Response (200 OK):**
```json
{
  "status": "healthy",
  "chroma_stats": {
    "collection_name": "confluence_jira_docs",
    "total_documents": 450,
    "persist_directory": "./chroma_db"
  },
  "retrieval_stats": {
    "chroma": {
      "total_documents": 450
    },
    "bm25": {
      "indexed": true,
      "num_documents": 450
    },
    "alpha": 0.5,
    "rrf_k": 60
  }
}
```

---

### 2. Query Knowledge Base 🔍

**Purpose:** Search documents using hybrid retrieval

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/query`
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "query": "How to configure authentication?",
    "top_k": 5,
    "method": "hybrid"
  }
  ```

**Postman Steps:**
1. Create new request
2. Set method to `POST`
3. Enter URL: `http://localhost:8000/query`
4. Go to **Headers** tab
   - Add: `Content-Type` = `application/json`
5. Go to **Body** tab
   - Select **raw**
   - Select **JSON** from dropdown
   - Paste the JSON above
6. Click **Send**

**Request Options:**
```json
{
  "query": "your search query here",
  "top_k": 5,                    // Number of results (1-20)
  "method": "hybrid",            // "hybrid", "dense", or "sparse"
  "filters": {                   // Optional metadata filters
    "doc_type": "confluence",
    "space": "ENG"
  }
}
```

**Expected Response (200 OK):**
```json
{
  "query": "How to configure authentication?",
  "results": [
    {
      "content": "Authentication configuration steps...",
      "metadata": {
        "doc_title": "Authentication Guide",
        "doc_url": "https://confluence.../auth-guide",
        "doc_type": "confluence",
        "space": "ENG"
      },
      "score": 0.8765
    }
  ],
  "total_results": 5,
  "method": "hybrid"
}
```

---

### 3. Chat with Bot 💬

**Purpose:** Have a conversation with RAG-powered bot

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/chat`
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "message": "What are the latest bugs in the project?",
    "top_k": 5,
    "use_jira_live": false
  }
  ```

**Postman Steps:**
1. Create new request
2. Set method to `POST`
3. Enter URL: `http://localhost:8000/chat`
4. Add header: `Content-Type: application/json`
5. Body → raw → JSON
6. Paste the JSON
7. Click **Send**

**Request Options:**
```json
{
  "message": "Your question here",
  "conversation_history": [      // Optional: for multi-turn conversations
    {
      "role": "user",
      "content": "Previous question"
    },
    {
      "role": "assistant",
      "content": "Previous answer"
    }
  ],
  "top_k": 5,                    // Number of context docs to retrieve
  "use_jira_live": true          // Fetch live Jira data for this query
}
```

**Expected Response (200 OK):**
```json
{
  "response": "Based on the documentation, the latest bugs include...",
  "sources": [
    {
      "title": "Bug Report - Auth Issue",
      "url": "https://jira.../PROJ-123",
      "type": "jira",
      "score": 0.85
    }
  ],
  "conversation_id": null
}
```

---

### 4. Index Data 📥

**Purpose:** Trigger data indexing from Confluence/Jira

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/index`
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "source": "confluence",
    "refresh": false
  }
  ```

**Postman Steps:**
1. Create new request
2. Set method to `POST`
3. Enter URL: `http://localhost:8000/index`
4. Add header: `Content-Type: application/json`
5. Body → raw → JSON
6. Paste the JSON
7. Click **Send**

**Request Options:**
```json
{
  "source": "confluence",   // "confluence", "jira", or "both"
  "refresh": false          // true = delete existing data first
}
```

**Expected Response (200 OK):**
```json
{
  "status": "started",
  "documents_indexed": 0,
  "chunks_created": 0,
  "message": "Indexing confluence data started in background"
}
```

**Note:** This runs in the background. Check server logs for progress.

---

### 5. Create Jira Issue 🎫

**Purpose:** Create a new Jira issue via the bot

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/jira/issue`
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "project_key": "PROJ",
    "summary": "Implement new authentication method",
    "description": "Based on the documentation review, we need to implement OAuth 2.0 authentication.",
    "issue_type": "Task",
    "priority": "High",
    "labels": ["authentication", "security"]
  }
  ```

**Postman Steps:**
1. Create new request
2. Set method to `POST`
3. Enter URL: `http://localhost:8000/jira/issue`
4. Add header: `Content-Type: application/json`
5. Body → raw → JSON
6. Paste the JSON (update `project_key` to your project)
7. Click **Send**

**Request Options:**
```json
{
  "project_key": "PROJ",           // REQUIRED: Your Jira project key
  "summary": "Issue title",        // REQUIRED
  "description": "Details here",   // REQUIRED
  "issue_type": "Task",            // Task, Bug, Story, etc.
  "priority": "High",              // Optional: Low, Medium, High, Critical
  "labels": ["label1", "label2"]   // Optional
}
```

**Expected Response (200 OK):**
```json
{
  "id": "10123",
  "key": "PROJ-456",
  "title": "Implement new authentication method",
  "content": "Summary: Implement new authentication method...",
  "url": "https://yourcompany.atlassian.net/browse/PROJ-456",
  "project": "PROJ",
  "issue_type": "Task",
  "status": "To Do",
  "priority": "High",
  "created": "2025-10-23T14:30:00.000+0000"
}
```

---

### 6. Update Jira Issue 📝

**Purpose:** Update an existing Jira issue

**Request:**
- **Method:** `PUT`
- **URL:** `http://localhost:8000/jira/issue/PROJ-123`
  - Replace `PROJ-123` with actual issue key
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "summary": "Updated: Implement OAuth 2.0",
    "status": "In Progress",
    "priority": "Critical"
  }
  ```

**Postman Steps:**
1. Create new request
2. Set method to `PUT`
3. Enter URL: `http://localhost:8000/jira/issue/PROJ-123`
4. Add header: `Content-Type: application/json`
5. Body → raw → JSON
6. Paste the JSON (only include fields you want to update)
7. Click **Send**

**Request Options (all optional):**
```json
{
  "summary": "New summary",
  "description": "New description",
  "status": "In Progress",       // Triggers workflow transition
  "priority": "Critical",
  "assignee": "user@example.com",
  "labels": ["new-label"]
}
```

---

### 7. Get Jira Issue 📄

**Purpose:** Retrieve details of a specific issue

**Request:**
- **Method:** `GET`
- **URL:** `http://localhost:8000/jira/issue/PROJ-123`
  - Replace `PROJ-123` with actual issue key

**Postman Steps:**
1. Create new request
2. Set method to `GET`
3. Enter URL: `http://localhost:8000/jira/issue/PROJ-123`
4. Click **Send**

---

### 8. Add Comment to Jira Issue 💬

**Purpose:** Add a comment to an issue

**Request:**
- **Method:** `POST`
- **URL:** `http://localhost:8000/jira/issue/PROJ-123/comment`
- **Headers:** 
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "comment": "This issue has been reviewed by the bot. Relevant documentation has been found."
  }
  ```

---

### 9. Search Jira Issues 🔎

**Purpose:** Search for issues using text query

**Request:**
- **Method:** `GET`
- **URL:** `http://localhost:8000/jira/search?query=authentication&max_results=20`

**Postman Steps:**
1. Create new request
2. Set method to `GET`
3. Enter URL with parameters
4. Click **Send**

**URL Parameters:**
- `query`: Search term (required)
- `max_results`: Number of results (default: 20)

---

## 📁 Postman Collection

### Import This Collection

Save this as `rag-bot-collection.json`:

```json
{
  "info": {
    "name": "Confluence & Jira RAG Bot",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/health",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["health"]
        }
      }
    },
    {
      "name": "Query - Hybrid",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"How to configure authentication?\",\n  \"top_k\": 5,\n  \"method\": \"hybrid\"\n}"
        },
        "url": {
          "raw": "http://localhost:8000/query",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["query"]
        }
      }
    },
    {
      "name": "Chat",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"message\": \"What are the latest bugs?\",\n  \"top_k\": 5,\n  \"use_jira_live\": true\n}"
        },
        "url": {
          "raw": "http://localhost:8000/chat",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["chat"]
        }
      }
    },
    {
      "name": "Create Jira Issue",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"project_key\": \"PROJ\",\n  \"summary\": \"Test issue from API\",\n  \"description\": \"This is a test issue created via the RAG bot API\",\n  \"issue_type\": \"Task\",\n  \"priority\": \"Medium\"\n}"
        },
        "url": {
          "raw": "http://localhost:8000/jira/issue",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["jira", "issue"]
        }
      }
    }
  ]
}
```

**To Import:**
1. Open Postman
2. Click **Import** (top left)
3. Select **Raw text**
4. Paste the JSON above
5. Click **Import**

---

## 🎯 Common Test Scenarios

### Scenario 1: Basic Flow Test

**Step 1:** Health Check
```
GET http://localhost:8000/health
```

**Step 2:** Query Documents
```
POST http://localhost:8000/query
Body: {"query": "authentication", "top_k": 3, "method": "hybrid"}
```

**Step 3:** Chat
```
POST http://localhost:8000/chat
Body: {"message": "Explain authentication setup"}
```

### Scenario 2: Jira Operations

**Step 1:** Search Issues
```
GET http://localhost:8000/jira/search?query=bug&max_results=5
```

**Step 2:** Get Specific Issue
```
GET http://localhost:8000/jira/issue/PROJ-123
```

**Step 3:** Create New Issue
```
POST http://localhost:8000/jira/issue
Body: {project_key, summary, description}
```

**Step 4:** Add Comment
```
POST http://localhost:8000/jira/issue/PROJ-123/comment
Body: {"comment": "Working on this"}
```

### Scenario 3: Different Retrieval Methods

**Test Dense (Semantic):**
```json
{
  "query": "secure login process",
  "method": "dense"
}
```

**Test Sparse (Keywords):**
```json
{
  "query": "OAuth token JWT",
  "method": "sparse"
}
```

**Test Hybrid (Best):**
```json
{
  "query": "how to implement authentication",
  "method": "hybrid"
}
```

---

## ⚠️ Troubleshooting

### Error: "Connection refused"
**Solution:** Start the server
```bash
python run.py
```

### Error: "No documents found"
**Solution:** Index data first
```bash
python scripts/index_data.py --source both
```

### Error: "Jira authentication failed"
**Solution:** Check `.env` file has correct Jira credentials

### Error: "Deployment not found"
**Solution:** Verify Azure OpenAI deployment names in `.env`

---

## 💡 Pro Tips

1. **Save Requests**: Save each request in Postman for reuse
2. **Use Variables**: Create environment variables for `{{baseUrl}}`
3. **Test Collections**: Create test scripts for automated testing
4. **Check Logs**: Watch server terminal for detailed error messages
5. **Copy Issue Keys**: Copy created issue keys from responses for updates

---

## 📊 Expected Response Times

| Endpoint | Typical Response Time |
|----------|----------------------|
| /health | < 100ms |
| /query | 500ms - 2s |
| /chat | 2s - 5s (includes LLM) |
| /jira/issue (create) | 1s - 3s |
| /jira/search | 500ms - 2s |
| /index | < 100ms (async) |

---

**Happy Testing! 🚀**

For more details, see the interactive API docs at: http://localhost:8000/docs
