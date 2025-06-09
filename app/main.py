import streamlit as st
import os
from dotenv import load_dotenv

from ui_components import render_query_interface, API_URL

# Load environment variables from root directory
load_dotenv(os.path.join("..", ".env"))

def main():
    st.set_page_config(
        page_title="GraphRAG Query Interface",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("GraphRAG Query")
    
    # Add API status indicator
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("Query interface for GraphRAG and Traditional RAG methods")
    
    with col2:
        # Check API connectivity
        try:
            import requests
            response = requests.get(f"{API_URL}/methods", timeout=2)
            if response.status_code == 200:
                st.success("🟢 API Connected")
            else:
                st.error("🔴 API Error")
        except:
            st.error("🔴 API Offline")
    
    # Render main query interface
    render_query_interface()

if __name__ == "__main__":
    main()