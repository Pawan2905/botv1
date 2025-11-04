# RAG Module

This module provides a reusable Retrieval-Augmented Generation (RAG) pipeline for indexing and querying documents from various sources. This initial version is focused on Confluence integration.

## Features

- **Modular Design**: The module is designed to be self-contained and easily reusable.
- **Confluence Integration**: Fetch and process documents from Confluence spaces.
- **Vector-Based Retrieval**: Utilizes a vector store for efficient document retrieval.

## Installation

1.  **Install Dependencies**: Ensure that the required packages are installed. You can add the following to your `requirements.txt` file:
    
    ```
    atlassian-python-api
    beautifulsoup4
    chromadb
    unstructured
    ```
    
2.  **Set Up Environment**: Make sure you have the necessary environment variables or a configuration file for your Confluence credentials.

## Usage

### Indexing Documents from Confluence

To index documents from a Confluence space, you can use the `RAG` class as follows:

```python
from rag_module.rag import RAG

# Initialize the RAG pipeline
rag_pipeline = RAG(
    chroma_persist_dir="path/to/your/db",
    chroma_collection_name="confluence_collection"
)

# Index a Confluence space
rag_pipeline.index_confluence_space(
    confluence_url="https://your-confluence-domain.atlassian.net",
    confluence_user="your-email@example.com",
    confluence_token="your-api-token",
    space_key="YOUR_SPACE_KEY"
)
```

### Querying Documents

Once the documents are indexed, you can perform queries to retrieve relevant information:

```python
# Perform a query
results = rag_pipeline.query(
    query_text="your query here",
    top_k=5
)

# Print the results
for result in results:
    print(f"Score: {result['score']:.4f}")
    print(f"Content: {result['content']}\\n")
```

This `README.md` provides a basic guide to using the RAG module. You can expand it with more detailed information as the module evolves.
