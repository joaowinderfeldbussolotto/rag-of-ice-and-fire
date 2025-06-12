import streamlit as st
import requests
import os
import time
API_URL = os.getenv("API_URL", "http://localhost:8000") + "/api/v1"

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
        
        # Run all selected searches with async polling
        with st.spinner("Starting searches..."):
            results = _run_selected_searches_async(query, selected)
        
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

def _run_selected_searches_async(query, selected_methods):
    """Run all selected searches using async API with polling"""
    # Start all tasks
    task_ids = {}
    for method in selected_methods:
        try:
            task_id = _start_async_request(query, method)
            if task_id:
                task_ids[method] = task_id
        except Exception as e:
            task_ids[method] = {"error": f"Failed to start: {str(e)}"}
    
    # Poll for results
    results = {}
    progress_bar = st.progress(0, text="Processing searches...")
    
    completed = 0
    total = len(task_ids)
    
    while completed < total:
        for method, task_id in task_ids.items():
            if method in results:
                continue  # Already completed
                
            if isinstance(task_id, dict) and "error" in task_id:
                results[method] = task_id
                completed += 1
                continue
            
            try:
                task_result = _poll_task_status(task_id)
                if task_result.get("status") == "completed":
                    results[method] = task_result.get("result", {})
                    completed += 1
                elif task_result.get("status") == "failed":
                    results[method] = {"error": "Task failed"}
                    completed += 1
            except Exception as e:
                results[method] = {"error": f"Polling failed: {str(e)}"}
                completed += 1
        
        # Update progress
        progress = completed / total
        progress_bar.progress(progress, text=f"Completed {completed}/{total} searches...")
        
        if completed < total:
            time.sleep(1)  # Poll every second
    
    progress_bar.empty()
    return results

def _start_async_request(query, method):
    """Start an async API request and return task ID"""
    try:
        payload = {
            "query": query,
            "method": method
        }
        
        response = requests.post(
            f"{API_URL}/query/async",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get("task_id")
        else:
            return None
    except Exception:
        return None

def _poll_task_status(task_id):
    """Poll for task status"""
    try:
        response = requests.get(
            f"{API_URL}/task/{task_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "failed", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def _make_sync_api_request(query, method):
    """Make synchronous API request"""
    try:
        payload = {
            "query": query,
            "method": method
        }
        
        response = requests.post(
            f"{API_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error {response.status_code}: {response.text}"}
    except requests.exceptions.Timeout:
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