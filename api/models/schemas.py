from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class RAGMethod(str, Enum):
    GRAPHRAG_LOCAL = "graphrag-localsearch"
    GRAPHRAG_GLOBAL = "graphrag-globalsearch" 
    GRAPHRAG_DRIFT = "graphrag-drift"
    NAIVE_RAG = "naiverag"

class ResponseType(str, Enum):
    SINGLE_PARAGRAPH = "Single Paragraph"
    MULTIPLE_PARAGRAPHS = "Multiple Paragraphs"
    SINGLE_SENTENCE = "Single Sentence"
    LIST_OF_POINTS = "List of Points"
    COMPREHENSIVE_REPORT = "Comprehensive Report"

class RAGRequest(BaseModel):
    query: str = Field(..., description="The question to ask", min_length=1)
    method: RAGMethod = Field(..., description="RAG method to use")
    
    # Optional parameters
    community_level: Optional[int] = Field(None, description="Community level for GraphRAG", ge=0, le=3)
    response_type: Optional[ResponseType] = Field(None, description="Type of response format")
    num_results: Optional[int] = Field(None, description="Number of results for naive RAG", ge=1, le=20)
    dynamic_community_selection: Optional[bool] = Field(False, description="Use dynamic community selection")

class RAGResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    method: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SystemStatus(BaseModel):
    graphrag_available: bool
    traditional_rag_available: bool
    project_directory: str
    data_summary: Optional[Dict[str, Any]] = None