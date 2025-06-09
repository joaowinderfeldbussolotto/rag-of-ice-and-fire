import logging
from typing import Dict, Any
from api.models.schemas import RAGRequest, RAGResponse, RAGMethod
from .graphrag_client import GraphRAGClient
from .traditional_rag_client import TraditionalRAGClient
from api.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Main service for orchestrating RAG operations"""
    
    def __init__(self):
        self.graphrag_client = GraphRAGClient(settings.PROJECT_DIRECTORY)
        self.traditional_rag_client = TraditionalRAGClient(
            settings.INPUT_DIRECTORY,
            settings.CHROMA_DB_PATH
        )

    
    async def process_query(self, request: RAGRequest) -> RAGResponse:
        """Process a RAG query based on the specified method"""
        try:
            logger.info(f"Processing query with method: {request.method}")
            
            if request.method == RAGMethod.GRAPHRAG_LOCAL:
                return await self._handle_graphrag_local(request)
            elif request.method == RAGMethod.GRAPHRAG_GLOBAL:
                return await self._handle_graphrag_global(request)
            elif request.method == RAGMethod.GRAPHRAG_DRIFT:
                return await self._handle_graphrag_drift(request)
            elif request.method == RAGMethod.NAIVE_RAG:
                return await self._handle_naive_rag(request)
            else:
                return RAGResponse(
                    success=False,
                    method=request.method,
                    error=f"Unsupported method: {request.method}"
                )
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return RAGResponse(
                success=False,
                method=request.method,
                error=f"Internal error: {str(e)}"
            )
    
    async def _handle_graphrag_local(self, request: RAGRequest) -> RAGResponse:
        """Handle GraphRAG local search"""
        community_level = request.community_level or settings.DEFAULT_COMMUNITY_LEVEL
        response_type = request.response_type or settings.DEFAULT_RESPONSE_TYPE
        
        result = await self.graphrag_client.query_local(
            query=request.query,
            community_level=community_level,
            response_type=response_type
        )
        
        if "error" in result:
            return RAGResponse(
                success=False,
                method=request.method,
                error=result["error"]
            )
        
        return RAGResponse(
            success=True,
            response=result.get("response"),
            method=request.method,
            metadata={
                "community_level": result.get("community_level"),
                "response_type": result.get("response_type"),
                "context_available": "context" in result
            }
        )
    
    async def _handle_graphrag_global(self, request: RAGRequest) -> RAGResponse:
        """Handle GraphRAG global search"""
        community_level = request.community_level or settings.DEFAULT_COMMUNITY_LEVEL
        response_type = request.response_type or settings.DEFAULT_RESPONSE_TYPE
        dynamic_selection = request.dynamic_community_selection or False
        
        result = await self.graphrag_client.query_global(
            query=request.query,
            community_level=community_level,
            response_type=response_type,
            dynamic_community_selection=dynamic_selection
        )
        
        if "error" in result:
            return RAGResponse(
                success=False,
                method=request.method,
                error=result["error"]
            )
        
        return RAGResponse(
            success=True,
            response=result.get("response"),
            method=request.method,
            metadata={
                "community_level": result.get("community_level"),
                "response_type": result.get("response_type"),
                "dynamic_community_selection": result.get("dynamic_community_selection"),
                "context_available": "context" in result
            }
        )
    
    async def _handle_graphrag_drift(self, request: RAGRequest) -> RAGResponse:
        """Handle GraphRAG drift search"""
        community_level = request.community_level or settings.DEFAULT_COMMUNITY_LEVEL
        response_type = request.response_type or settings.DEFAULT_RESPONSE_TYPE
        
        result = await self.graphrag_client.query_drift(
            query=request.query,
            community_level=community_level,
            response_type=response_type
        )
        
        if "error" in result:
            return RAGResponse(
                success=False,
                method=request.method,
                error=result["error"]
            )
        
        return RAGResponse(
            success=True,
            response=result.get("response"),
            method=request.method,
            metadata={
                "community_level": result.get("community_level"),
                "response_type": result.get("response_type"),
                "drift_analysis": result.get("drift_analysis"),
                "context_available": "context" in result
            }
        )
    
    async def _handle_naive_rag(self, request: RAGRequest) -> RAGResponse:
        """Handle traditional/naive RAG"""
        if not self.traditional_rag_client.is_available():
            return RAGResponse(
                success=False,
                method=request.method,
                error="Traditional RAG is not available. Check dependencies and configuration."
            )
        
        # Run the sync method in a thread pool to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.traditional_rag_client.query_traditional, 
            request.query
        )
        
        if "error" in result:
            return RAGResponse(
                success=False,
                method=request.method,
                error=result["error"]
            )
        
        return RAGResponse(
            success=True,
            response=result.get("response"),
            method=request.method,
            metadata={
                "num_docs_retrieved": result.get("num_docs_retrieved", 0),
                "retrieved_docs_available": "retrieved_docs" in result
            }
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and availability"""
        return {
            "graphrag_available": hasattr(self.graphrag_client, 'graphrag_config') and self.graphrag_client.graphrag_config is not None,
            "traditional_rag_available": self.traditional_rag_client.is_available(),
            "project_directory": settings.PROJECT_DIRECTORY,
            "data_summary": self.graphrag_client.get_data_summary() if self.graphrag_client else None
        }
    
    async def build_graphrag_index(self) -> Dict[str, Any]:
        """Build GraphRAG index"""
        return await self.graphrag_client.build_index()

    async def get_document_count(self) -> int:
        """Get the number of documents in the index"""
        # RUN IN THREAD POOL
        # to avoid blocking the event loop  
        import asyncio
        loop = asyncio.get_event_loop()
        # Run the sync method in a thread pool to avoid blocking the event loop
        result = await loop.run_in_executor(
            None, 
            self.traditional_rag_client .get_document_count
        )
        if "error" in result:
            raise Exception(result["error"])

        return result
    
    
