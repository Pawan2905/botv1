# Data Fetching Options

This guide explains how to control what data gets fetched from Confluence and Jira.

## 🎯 Quick Summary

| Configuration | What Gets Fetched |
|---------------|-------------------|
| `CONFLUENCE_SPACE_KEY=ENG` | ✅ Only pages from "ENG" space |
| `CONFLUENCE_SPACE_KEY=` (blank) | ⚠️ ALL pages from ALL spaces |
| `JIRA_PROJECT_KEY=PROJ` | ✅ Only issues from "PROJ" project |
| `JIRA_PROJECT_KEY=` (blank) | ⚠️ ALL issues from ALL projects |

## 📖 Detailed Explanation

### Confluence Space Key

**Option 1: Specific Space (Recommended)**
```env
CONFLUENCE_SPACE_KEY=ENG
```
- ✅ Fetches only pages from the "ENG" space
- ✅ Faster indexing
- ✅ Lower API usage
- ✅ More focused knowledge base

**How to find your space key:**
1. Go to your Confluence space
2. Click **Space Settings** (bottom left)
3. The space key is shown in the URL: `https://your-domain.atlassian.net/wiki/spaces/ENG/overview`
   - In this example, the space key is `ENG`

**Option 2: Multiple Spaces**
To fetch from multiple specific spaces, you need to run the indexing script multiple times or modify the code. For now, leave it blank or pick the most important space.

**Option 3: All Spaces (Not Recommended)**
```env
CONFLUENCE_SPACE_KEY=
# Or comment it out:
# CONFLUENCE_SPACE_KEY=
```
- ⚠️ Fetches pages from ALL accessible spaces
- ⚠️ May take a very long time (could be thousands of pages)
- ⚠️ May hit Atlassian rate limits
- ⚠️ Uses more ChromaDB storage

### Jira Project Key

**Option 1: Specific Project (Recommended)**
```env
JIRA_PROJECT_KEY=PROJ
```
- ✅ Fetches only issues from the "PROJ" project
- ✅ Faster indexing
- ✅ Lower API usage
- ✅ More focused knowledge base

**How to find your project key:**
1. Go to your Jira project
2. Look at the issue keys (e.g., `PROJ-123`, `PROJ-456`)
3. The project key is the part before the dash: `PROJ`
4. Or go to **Project Settings** → **Details** to see the project key

**Option 2: All Projects (Not Recommended)**
```env
JIRA_PROJECT_KEY=
# Or comment it out:
# JIRA_PROJECT_KEY=
```
- ⚠️ Fetches issues from ALL accessible projects
- ⚠️ May take a very long time (could be thousands of issues)
- ⚠️ May hit Atlassian rate limits
- ⚠️ Uses more ChromaDB storage

## 🎨 Common Configuration Scenarios

### Scenario 1: Single Team/Department
```env
# Engineering team's Confluence space and Jira project
CONFLUENCE_SPACE_KEY=ENG
JIRA_PROJECT_KEY=ENGPROJ
```

### Scenario 2: Documentation Only
```env
# Only documentation space, no Jira
CONFLUENCE_SPACE_KEY=DOCS
JIRA_PROJECT_KEY=  # Leave blank or comment out

# When indexing, use:
# python scripts/index_data.py --source confluence
```

### Scenario 3: Support/Helpdesk
```env
# Support documentation and support tickets
CONFLUENCE_SPACE_KEY=SUPPORT
JIRA_PROJECT_KEY=HELP
```

### Scenario 4: Company-wide Knowledge Base (Advanced)
```env
# Fetch everything (use with caution!)
CONFLUENCE_SPACE_KEY=
JIRA_PROJECT_KEY=

# Consider setting limits in the indexing script
```

## 🛠️ Advanced: Filtering at Index Time

You can also filter when running the indexing script:

### Filter by Date (for Jira)

Modify `scripts/index_data.py` to add date filters:

```python
# In the Jira fetching section, modify the JQL
jql = f"project = {project_key} AND updated >= -30d ORDER BY updated DESC"
```

### Fetch Multiple Specific Spaces

Create a custom script:

```python
from data_fetchers import ConfluenceFetcher
from config import settings

confluence = ConfluenceFetcher(
    url=settings.confluence_url,
    username=settings.confluence_username,
    api_token=settings.confluence_api_token
)

# Fetch from multiple spaces
spaces = ["ENG", "DOCS", "SUPPORT"]
all_pages = []

for space_key in spaces:
    confluence.space_key = space_key
    pages = confluence.fetch_all_pages()
    all_pages.extend(pages)

print(f"Fetched {len(all_pages)} pages from {len(spaces)} spaces")
```

## 📊 Performance Comparison

| Scope | Pages/Issues | Indexing Time | Embedding Cost |
|-------|--------------|---------------|----------------|
| Single space/project | ~100 | ~5 minutes | ~$0.01 |
| 3-5 spaces/projects | ~500 | ~20 minutes | ~$0.05 |
| All spaces/projects | ~5000+ | ~2+ hours | ~$0.50+ |

*Times are approximate and depend on content size and API speed*

## 🎯 Recommendations

### For Development/Testing
```env
# Use a small, specific space/project
CONFLUENCE_SPACE_KEY=TEST
JIRA_PROJECT_KEY=DEMO
```

### For Production
```env
# Use the most relevant space/project for your team
CONFLUENCE_SPACE_KEY=YOURTEAM
JIRA_PROJECT_KEY=YOURPROJECT
```

### For Multiple Teams
Consider running separate instances with different configurations, or:
1. Index data separately for each team
2. Use different ChromaDB collections
3. Provide team-specific endpoints

## 💡 Tips

1. **Start Small**: Begin with one space/project, then expand
2. **Monitor Costs**: Azure OpenAI charges per embedding token
3. **Rate Limits**: Atlassian has API rate limits (~180 requests/minute)
4. **Storage**: More data = larger ChromaDB database
5. **Relevance**: More focused data = better search results

## 🔄 Changing Configuration Later

To switch spaces/projects:

1. Update `.env` file
2. Run indexing with `--refresh` flag:
   ```bash
   python scripts/index_data.py --source both --refresh
   ```
3. This will delete old data and re-index with new filters

Or to ADD data from another space/project without deleting:
```bash
# Don't use --refresh flag
python scripts/index_data.py --source confluence
```

## ❓ FAQ

**Q: Can I fetch from multiple specific spaces?**  
A: Currently, you need to modify the code or run indexing multiple times. See "Advanced: Filtering at Index Time" above.

**Q: What if I leave both keys blank?**  
A: It will try to fetch ALL data, which may take hours and hit rate limits.

**Q: Can I fetch only recent Jira issues?**  
A: Yes, modify the JQL query in `data_fetchers/jira_fetcher.py` to add date filters.

**Q: How do I know what spaces/projects I have access to?**  
A: Log into Confluence/Jira and check the sidebar or project list.

**Q: Does leaving the key blank cost more?**  
A: Yes - more documents = more embeddings = higher Azure OpenAI costs.

---

**Recommendation**: Always specify specific space and project keys unless you explicitly need all data.
