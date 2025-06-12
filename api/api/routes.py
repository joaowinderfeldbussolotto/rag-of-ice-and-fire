from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from api.models.schemas import RAGRequest, RAGResponse, SystemStatus, AsyncRAGRequest, TaskResult, TaskStatus
from api.services.rag_service import RAGService
from api.services.task_manager import task_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get RAG service
def get_rag_service() -> RAGService:
    return RAGService()

async def process_rag_task(task_id: str, request: RAGRequest, rag_service: RAGService):
    """Background task to process RAG request"""
    try:
        task_manager.update_task_status(task_id, TaskStatus.RUNNING)
        response = await rag_service.process_query(request)
        task_manager.complete_task(task_id, response)
    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}")
        task_manager.fail_task(task_id, str(e))

@router.post("/query", response_model=RAGResponse)
async def query_rag(
    request: RAGRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """Query the RAG system with the specified method (synchronous)"""
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

@router.post("/query/async")
async def query_rag_async(
    request: RAGRequest,
    background_tasks: BackgroundTasks,
    rag_service: RAGService = Depends(get_rag_service)
):
    """Start an async RAG query and return task ID"""
    try:
        task_id = task_manager.create_task()
        background_tasks.add_task(process_rag_task, task_id, request, rag_service)
        
        return {"task_id": task_id, "status": "started"}
    
    except Exception as e:
        logger.error(f"Error starting async query: {e}")
        raise HTTPException(status_code=500, detail="Error starting async query")

@router.get("/task/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """Get the status of an async task"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

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