"""MCP Server for integrating multiple data sources."""

import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Model Context Protocol (MCP) server for managing multiple data sources.
    
    This server provides a unified interface for connecting and querying
    multiple data sources (Confluence, Jira, and potentially others).
    """
    
    def __init__(self):
        """Initialize MCP server."""
        self.data_sources = {}
        self.source_configs = {}
        logger.info("Initialized MCP Server")
    
    def register_data_source(
        self,
        name: str,
        source_type: str,
        fetcher: Any,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a new data source with the MCP server.
        
        Args:
            name: Unique name for the data source
            source_type: Type of source ('confluence', 'jira', etc.)
            fetcher: Fetcher instance for this source
            config: Optional configuration for the source
        """
        self.data_sources[name] = {
            "type": source_type,
            "fetcher": fetcher,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        if config:
            self.source_configs[name] = config
        
        logger.info(f"Registered data source: {name} (type: {source_type})")
    
    def unregister_data_source(self, name: str) -> bool:
        """
        Unregister a data source.
        
        Args:
            name: Name of the data source
            
        Returns:
            True if successful, False otherwise
        """
        if name in self.data_sources:
            del self.data_sources[name]
            if name in self.source_configs:
                del self.source_configs[name]
            logger.info(f"Unregistered data source: {name}")
            return True
        return False
    
    def get_data_source(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a data source.
        
        Args:
            name: Name of the data source
            
        Returns:
            Data source information or None
        """
        return self.data_sources.get(name)
    
    def list_data_sources(self) -> List[Dict[str, Any]]:
        """
        List all registered data sources.
        
        Returns:
            List of data source information
        """
        return [
            {
                "name": name,
                "type": info["type"],
                "status": info["status"],
                "registered_at": info["registered_at"]
            }
            for name, info in self.data_sources.items()
        ]
    
    def fetch_from_source(
        self,
        source_name: str,
        query: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from a specific source.
        
        Args:
            source_name: Name of the data source
            query: Optional query/filter
            max_results: Maximum number of results
            
        Returns:
            List of documents from the source
        """
        if source_name not in self.data_sources:
            logger.error(f"Data source not found: {source_name}")
            return []
        
        source = self.data_sources[source_name]
        fetcher = source["fetcher"]
        source_type = source["type"]
        
        try:
            if source_type == "confluence":
                if query:
                    return fetcher.search_pages(f'text ~ "{query}"', limit=max_results)
                else:
                    return fetcher.fetch_all_pages(limit=max_results)
            
            elif source_type == "jira":
                if query:
                    return fetcher.search_issues(query, max_results=max_results)
                else:
                    return fetcher.fetch_all_issues(max_results=max_results)
            
            else:
                logger.warning(f"Unknown source type: {source_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return []
    
    def fetch_from_all_sources(
        self,
        query: Optional[str] = None,
        max_results_per_source: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch data from all registered sources.
        
        Args:
            query: Optional query/filter
            max_results_per_source: Maximum results per source
            
        Returns:
            Dictionary mapping source names to their results
        """
        all_results = {}
        
        for source_name in self.data_sources.keys():
            logger.info(f"Fetching from source: {source_name}")
            results = self.fetch_from_source(
                source_name=source_name,
                query=query,
                max_results=max_results_per_source
            )
            all_results[source_name] = results
            logger.info(f"Fetched {len(results)} items from {source_name}")
        
        return all_results
    
    def aggregate_results(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        merge_strategy: str = "append"
    ) -> List[Dict[str, Any]]:
        """
        Aggregate results from multiple sources.
        
        Args:
            results: Dictionary of results from different sources
            merge_strategy: How to merge results ('append', 'deduplicate', etc.)
            
        Returns:
            Aggregated list of documents
        """
        if merge_strategy == "append":
            # Simply concatenate all results
            aggregated = []
            for source_name, source_results in results.items():
                for item in source_results:
                    item["mcp_source"] = source_name
                    aggregated.append(item)
            return aggregated
        
        elif merge_strategy == "deduplicate":
            # Deduplicate based on content hash
            seen_hashes = set()
            aggregated = []
            
            for source_name, source_results in results.items():
                for item in source_results:
                    content_hash = hash(item.get("content", "")[:200])
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        item["mcp_source"] = source_name
                        aggregated.append(item)
            
            return aggregated
        
        else:
            logger.warning(f"Unknown merge strategy: {merge_strategy}")
            return []
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all registered sources.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_sources": len(self.data_sources),
            "sources": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for name, info in self.data_sources.items():
            stats["sources"][name] = {
                "type": info["type"],
                "status": info["status"],
                "registered_at": info["registered_at"]
            }
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all sources.
        
        Returns:
            Health status for all sources
        """
        health = {
            "overall_status": "healthy",
            "sources": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for name, info in self.data_sources.items():
            try:
                # Try a simple fetch to check if source is accessible
                fetcher = info["fetcher"]
                source_type = info["type"]
                
                if source_type == "confluence":
                    fetcher.fetch_all_pages(limit=1)
                elif source_type == "jira":
                    fetcher.fetch_all_issues(max_results=1)
                
                health["sources"][name] = {
                    "status": "healthy",
                    "type": source_type
                }
            except Exception as e:
                health["sources"][name] = {
                    "status": "unhealthy",
                    "type": info["type"],
                    "error": str(e)
                }
                health["overall_status"] = "degraded"
                logger.error(f"Health check failed for {name}: {e}")
        
        return health
    
    def export_configuration(self) -> str:
        """
        Export MCP configuration as JSON.
        
        Returns:
            JSON string with configuration
        """
        config = {
            "version": "1.0",
            "sources": {}
        }
        
        for name, source_config in self.source_configs.items():
            config["sources"][name] = {
                "type": self.data_sources[name]["type"],
                "config": source_config
            }
        
        return json.dumps(config, indent=2)
