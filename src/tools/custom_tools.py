"""
Custom tools for the News Agent.
"""
from langchain_core.tools import tool
from typing import Optional

@tool
def get_current_date() -> str:
    """
    Returns the current date in YYYY-MM-DD format.
    Use this tool to get the current date for news research.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

@tool
def simple_calculator(expression: str) -> str:
    """
    A simple calculator that can evaluate mathematical expressions.
    
    Args:
        expression: A string representing a mathematical expression (e.g., "2 + 2 * 10").
        
    Returns:
        The result of the expression as a string, or an error message.
    """
    try:
        # A simple, safer way to evaluate expressions
        # For a real-world scenario, use a more robust library like 'numexpr'
        allowed_chars = "0123456789+-*/(). "
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression."
        
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

def valyu_search(query: str, site_filter: Optional[str] = None, max_results: int = 5) -> list:
    """
    Performs a search using the Valyu API.

    Args:
        query: The search query.
        site_filter: A specific site to filter the search results.
        max_results: The maximum number of results to return.

    Returns:
        A list of search results, or an empty list if an error occurs.
    """
    # This is a mock implementation. In a real scenario, you would integrate
    # with the actual Valyu API.
    print(f"--- MOCK VALYU SEARCH ---")
    print(f"Query: {query}")
    if site_filter:
        print(f"Site Filter: {site_filter}")
    
    # Simulate returning a list of search result dictionaries
    mock_results = [
        {
            "url": f"https://mock-valyu-result.com/{query.replace(' ', '-')}/{i}",
            "title": f"Mock Result {i} for {query}",
            "snippet": f"This is a mock search result snippet for query '{query}'."
        } for i in range(max_results)
    ]
    return mock_results

class ValyuSearchTool:
    def search(self, query: str, site_filter: Optional[str] = None, max_results: int = 5) -> list:
        return valyu_search(query, site_filter, max_results)
