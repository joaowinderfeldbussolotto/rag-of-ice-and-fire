from fastapi import APIRouter, HTTPException, Depends
from api.models.schemas import RAGRequest, RAGResponse, SystemStatus
from api.services.rag_service import RAGService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get RAG service
def get_rag_service() -> RAGService:
    return RAGService()

@router.post("/query", response_model=RAGResponse)
async def query_rag(
    request: RAGRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """Query the RAG system with the specified method"""
    try:
        response = await rag_service.process_query(request)
        
        if not response.success:
            raise HTTPException(status_code=400, detail=response.error)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status", response_model=SystemStatus)
async def get_status(rag_service: RAGService = Depends(get_rag_service)):
    """Get system status and availability"""
    try:
        status_data = rag_service.get_system_status()
        return SystemStatus(**status_data)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving system status")

@router.post("/build-index")
async def build_index(rag_service: RAGService = Depends(get_rag_service)):
    """Build GraphRAG index"""
    try:
        result = await rag_service.build_graphrag_index()
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building index: {e}")
        raise HTTPException(status_code=500, detail="Error building index")

@router.get("/document-count")
async def get_document_count(rag_service: RAGService = Depends(get_rag_service)):
    """Get the number of documents in the index"""
    try:
        count = await rag_service.get_document_count()
        return {"document_count": count}
    except Exception as e:
        logger.error(f"Error getting document count: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving document count")

@router.get("/methods")
async def get_available_methods():
    """Get available RAG methods"""
    return {
        "methods": [
            {
                "name": "naiverag",
                "description": "Traditional RAG using ChromaDB and embeddings",
                "display_name": "Traditional RAG"
            },	
            {
                "name": "graphrag-localsearch",
                "description": "GraphRAG local search using entities and relationships",
                "display_name": "GraphRAG Local Search"
            },
            {
                "name": "graphrag-globalsearch", 
                "description": "GraphRAG global search using community reports",
                "display_name": "GraphRAG Global Search"
            },
            # {
            #     "name": "graphrag-drift",
            #     "description": "GraphRAG drift search for temporal and contextual analysis",
            #     "display_name": "GraphRAG Drift Search",
            # },
        ]
    }