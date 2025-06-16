import requests
import json
import os
from typing import Dict, Any, List
from IPython.display import display, Markdown
import pandas as pd

# Notebook configuration for full content display
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', None)
pd.set_option('display.max_seq_items', None)

def compare_query_methods(query: str, methods: List[str], base_url: str = None) -> str:
    """
    Compare responses from the same query using different methods side by side.
    
    Args:
        query: The query string to send
        methods: List of method names to compare
        base_url: Base URL for the API (default: from API_URL env var or localhost:8000)
    
    Returns:
        Markdown formatted string with side-by-side comparison
    """
    if base_url is None:
        base_url = os.getenv('API_URL', 'http://localhost:8000')
    
    endpoint = f"{base_url}/api/v1/query"
    responses = {}
    
    # Collect responses for each method
    for method in methods:
        try:
            response = requests.post(
                endpoint,
                json={"query": query, "method": method},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                responses[method] = data
            else:
                responses[method] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "method": method
                }
        except Exception as e:
            responses[method] = {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "method": method
            }
    
    # Generate simple side-by-side comparison
    markdown = f"## Query: {query}\n\n"
    
    # Create simple columns
    markdown += '<div style="display: flex; gap: 20px; flex-wrap: wrap;">\n'
    
    for method in methods:
        resp = responses[method]
        markdown += f'<div style="flex: 1; min-width: 300px; border: 1px solid #ccc; padding: 15px;">\n'
        markdown += f'<h3>{method}</h3>\n'
        
        if not resp.get("success", True) or resp.get("error"):
            markdown += f'<p><strong>Error:</strong> {resp.get("error", "Unknown error")}</p>\n'
        else:
            if resp.get("response"):
                # Render markdown content directly without HTML conversion
                markdown += f'\n{resp["response"]}\n\n'
            else:
                markdown += '<p>No response content</p>\n'
        
        markdown += '</div>\n'
    
    markdown += '</div>\n\n'
    
    return markdown

# Example usage function
def display_comparison(query: str, methods: List[str]):
    """
    Display a comparison for the specified methods.
    Uses IPython's display(Markdown()) for rich rendering with proper markdown support.
    """
    comparison_md = compare_query_methods(query, methods)
    display(Markdown(comparison_md))
    return comparison_md