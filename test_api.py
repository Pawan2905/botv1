"""Simple test script to verify the API is working."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_health():
    """Test health endpoint."""
    print_section("Testing Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Status: {data['status']}")
        print(f"✓ ChromaDB Documents: {data['chroma_stats'].get('total_documents', 0)}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_query():
    """Test query endpoint."""
    print_section("Testing Query Endpoint")
    
    queries = [
        {"query": "authentication", "method": "hybrid"},
        {"query": "bug fix", "method": "dense"},
        {"query": "API documentation", "method": "sparse"},
        {"query": "What is the process for fixing bugs?"}
    ]
    
    for q in queries:
        try:
            payload = {"query": q["query"], "top_k": 3}
            if "method" in q:
                payload["method"] = q["method"]
            
            print(f"\nQuery: '{q['query']}' (method: {q.get('method', 'default')})")
            response = requests.post(
                f"{BASE_URL}/query",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✓ Found {data['total_results']} results")
            
            if data['results']:
                for i, result in enumerate(data['results'][:2], 1):
                    metadata = result.get('metadata', {})
                    print(f"  {i}. {metadata.get('doc_title', 'N/A')} "
                          f"({metadata.get('doc_type', 'N/A')}) "
                          f"- Score: {result.get('score', 0):.3f}")
        except Exception as e:
            print(f"✗ Query failed: {e}")


def test_chat():
    """Test chat endpoint."""
    print_section("Testing Chat Endpoint")
    
    messages = [
        "What documentation is available?",
        "Show me information about bugs",
        "What are the latest updates?"
    ]
    
    for message in messages:
        try:
            print(f"\nMessage: '{message}'")
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"message": message, "top_k": 3}
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✓ Response: {data['response'][:150]}...")
            print(f"✓ Sources: {len(data['sources'])}")
            
            if data['sources']:
                for source in data['sources'][:2]:
                    print(f"  - {source['title']} ({source['type']})")
        except Exception as e:
            print(f"✗ Chat failed: {e}")


def test_jira_search():
    """Test Jira search endpoint."""
    print_section("Testing Jira Search")
    
    try:
        print("\nSearching Jira issues...")
        response = requests.get(
            f"{BASE_URL}/jira/search",
            params={"query": "bug", "max_results": 5}
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Found {data['total']} issues")
        
        if data['results']:
            for issue in data['results'][:3]:
                print(f"  - {issue['key']}: {issue['title'][:60]}... "
                      f"(Status: {issue['status']})")
    except Exception as e:
        print(f"✗ Jira search failed: {e}")
        print("  Note: This is expected if Jira is not configured or has no data")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  API Test Suite - Confluence & Jira RAG Bot")
    print("=" * 80)
    print(f"\nTesting API at: {BASE_URL}")
    print("Make sure the server is running: python run.py")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    # Run tests
    if not test_health():
        print("\n✗ Health check failed. Make sure:")
        print("  1. Server is running (python run.py)")
        print("  2. Data is indexed (python scripts/index_data.py --source both)")
        return
    
    test_query()
    test_chat()
    test_jira_search()
    
    print_section("Test Suite Completed")
    print("\n✓ All tests completed!")
    print("\nNext steps:")
    print("  - Visit http://localhost:8000/docs for interactive API docs")
    print("  - Try creating a Jira issue via the API")
    print("  - Experiment with different retrieval methods")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
