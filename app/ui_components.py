import streamlit as st
import asyncio
import requests
import aiohttp
from dotenv import load_dotenv
API_URL = 'http://localhost:8000/api/v1'

def render_query_interface():
    """Render the main query interface"""
    # Query input
    query = st.text_area(
        "Search Query",
        height=80,
        key="search_query",
        placeholder="Enter your question..."
    )
    
    # Fetch available methods
    available_methods = _get_available_methods()
    
    if not available_methods:
        st.error("Could not fetch available methods")
        return
    
    # Search method selection - dynamic columns based on available methods
    num_methods = len(available_methods)
    num_cols = min(num_methods + 1, 5)  # +1 for search button, max 5 columns
    cols = st.columns([1] * num_cols)
    
    selected_methods = {}
    
    # Create checkboxes for each available method
    for i, method in enumerate(available_methods):
        if i < num_cols - 1:  # Leave last column for search button
            with cols[i]:
                selected_methods[method['name']] = st.checkbox(
                    method['display_name'], 
                    value=(i == 0)  # First method selected by default
                )
    
    # Search button in last column
    with cols[-1]:
        search_button = st.button("Search", type="primary")
    
    # Run search
    if search_button:
        if not query.strip():
            st.warning("Please enter a search query.")
            return
        
        selected = [method for method, selected in selected_methods.items() if selected]
        if not selected:
            st.warning("Please select at least one search method.")
            return
        
        # Run all selected searches simultaneously
        with st.spinner("Running searches..."):
            results = asyncio.run(_run_selected_searches_concurrently(query, selected))
        
        # Display results
        st.divider()
        
        # Display results based on number of methods selected
        if len(results) == 1:
            # Single result - use full width
            for method, result in results.items():
                _display_search_result_minimal(result)
        elif len(results) == 2:
            # Two results - side by side
            col1, col2 = st.columns(2)
            result_items = list(results.items())
            
            with col1:
                method, result = result_items[0]
                st.markdown(f"**{_get_method_display_name_by_key(method, available_methods)}**")
                _display_search_result_minimal(result)
            
            with col2:
                method, result = result_items[1]
                st.markdown(f"**{_get_method_display_name_by_key(method, available_methods)}**")
                _display_search_result_minimal(result)
        else:
            # Three or more results - use tabs
            tabs = [_get_method_display_name_by_key(method, available_methods) for method in results.keys()]
            tab_objects = st.tabs(tabs)
            
            for i, (method, result) in enumerate(results.items()):
                with tab_objects[i]:
                    _display_search_result_minimal(result)

def _get_available_methods():
    """Fetch available methods from the API"""
    try:
        response = requests.get(f"{API_URL}/methods", timeout=5)
        if response.status_code == 200:
            return response.json().get('methods')
        else:
            st.error(f"API returned status code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to API: {str(e)}")
        return []

async def _run_selected_searches_concurrently(query, selected_methods):
    """Run all selected searches concurrently via HTTP API"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        # Create tasks for selected searches
        for method in selected_methods:
            task = _make_api_request(session, query, method)
            tasks.append(task)
        
        # Run all tasks concurrently
        if tasks:
            try:
                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Map results back to method names and handle exceptions
                results = {}
                for i, result in enumerate(results_list):
                    method = selected_methods[i]
                    if isinstance(result, Exception):
                        results[method] = {"error": f"Search failed: {str(result)}"}
                    else:
                        results[method] = result
                
                return results
            except Exception as e:
                # Fallback error handling
                error_result = {"error": f"Concurrent execution failed: {str(e)}"}
                return {method: error_result for method in selected_methods}
        
        return {}

async def _make_api_request(session, query, method):
    try:
        payload = {
            "query": query,
            "method": method
        }
        
        async with session.post(
            f"{API_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                return {"error": f"API error {response.status}: {error_text}"}
    except asyncio.TimeoutError:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def _get_method_display_name_by_key(method_name: str, available_methods: list) -> str:
    """Get display name for search method by method name"""
    for method in available_methods:
        if method['name'] == method_name:
            return method['display_name']
    return method_name

def _get_method_display_name(method: dict) -> str:
    """Get display name for search method object"""
    return method.get('display_name', method.get('name', 'Unknown Method'))

def _display_search_result_minimal(result: dict):
    """Minimal display for search results"""
    # Check if there's actually an error (not just the error key with None value)
    has_error = not result.get("success", True) or (result.get("error") is not None)
    
    if has_error:
        error_msg = result.get("error", "Unknown error occurred")
        st.error(error_msg)
    else:
        # Display the response content
        response_text = result.get("response", "No response available")
        st.markdown(response_text)
        
        # Show metadata if available
        metadata = result.get("metadata")
        if metadata:
            with st.expander("Query Details", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    if "method" in result:
                        st.text(f"Method: {result['method']}")
                    if "community_level" in metadata:
                        st.text(f"Community Level: {metadata['community_level']}")
                    if "num_docs_retrieved" in metadata:
                        st.text(f"Docs Retrieved: {metadata['num_docs_retrieved']}")
                
                with col2:
                    if "response_type" in metadata:
                        st.text(f"Response Type: {metadata['response_type']}")
                    if "context_available" in metadata:
                        st.text(f"Context Available: {metadata['context_available']}")
                    if "retrieved_docs_available" in metadata:
                        st.text(f"Docs Available: {metadata['retrieved_docs_available']}")