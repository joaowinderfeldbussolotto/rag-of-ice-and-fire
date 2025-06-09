import os
from pathlib import Path
from typing import Dict
import logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb import Documents, EmbeddingFunction, Embeddings
    from langchain.chat_models import init_chat_model
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_mistralai import MistralAIEmbeddings
    TRADITIONAL_RAG_AVAILABLE = True
except ImportError as e:
    TRADITIONAL_RAG_AVAILABLE = False
    logger.warning(f"Traditional RAG dependencies not available: {e}")

import chromadb.utils.embedding_functions as embedding_functions
mistral_embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("GRAPHRAG_API_KEY"),
                api_base="https://api.mistral.ai/v1",
                model_name="mistral-embed"
            )


class MistralEmbeddingFunction(EmbeddingFunction):
    
    def __init__(self, api_key: str):
        if not TRADITIONAL_RAG_AVAILABLE:
            raise ImportError("Traditional RAG dependencies not available")
        
        self.embeddings = MistralAIEmbeddings(
            model="mistral-embed",
            api_key=api_key
        )
    
    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            texts = [input]
        elif isinstance(input, list):
            texts = input
        else:
            raise ValueError("Input must be a string or list of strings")
        
        if len(texts) == 1:
            embedding = self.embeddings.embed_query(texts[0])
            return [embedding]
        else:
            embeddings = self.embeddings.embed_documents(texts)
            return embeddings

class TraditionalRAGClient:
    
    def __init__(self, input_directory: str = "../ragtest/input/", chroma_db_path: str = "../rag/chromadb"):
        self.input_directory = Path(input_directory)
        self.chroma_db_path = Path(chroma_db_path)
        self.chroma_client = None
        self.collection = None
        self.llm = None
        self.rag_chain = None
        self.embedding_function = None
        self._setup_successful = False
        
        self.api_key = os.getenv('GRAPHRAG_API_KEY')
        
        if TRADITIONAL_RAG_AVAILABLE and self.api_key:
            try:
                self._setup_successful = self._setup_traditional_rag()
            except Exception as e:
                logger.error(f"Error during Traditional RAG setup: {e}")
                self._setup_successful = False
        else:
            logger.warning("Traditional RAG not available - missing dependencies or API key")
    
    def _setup_traditional_rag(self) -> bool:
        try:
            if not TRADITIONAL_RAG_AVAILABLE:
                return False
            
            if not self.api_key:
                return False
            
            self.embedding_function = MistralEmbeddingFunction(self.api_key)
            
            self.chroma_db_path.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_db_path))
            
            self.collection = self.chroma_client.get_collection(name="collection", embedding_function=mistral_embedding_function)
            self.llm = init_chat_model(
                "mistral-medium-latest", 
                model_provider="mistralai", 
                temperature=0, 
                api_key=settings.MISTRAL_API_KEY,
                max_retries=5
            )
            
            rag_prompt_template = """
Generate a response that responds to the user's question, summarizing all information in the input data tables appropriate for the response, and incorporating any relevant general knowledge.

If you don't know the answer, just say so. Do not make anything up.

Do not include information where the supporting evidence for it is not provided.
Do not answer unless its totally specified in the context

Context: {retrieved_docs}

User Question: {query}
"""
            
            rag_prompt = ChatPromptTemplate.from_template(rag_prompt_template)
            self.rag_chain = rag_prompt | self.llm | StrOutputParser()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up traditional RAG: {e}")
            return False
    
    def retrieval(self, query: str, num_results: int = 5) -> Dict:
        try:
            if not self.collection:
                return {"documents": [[]]}
            
            results = self.collection.query(
                query_texts=[query],
                n_results=num_results
            )
            
            return results
                
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return {"documents": [[]]}
    
    def _run_rag_chain(self, retrieved_docs: list, query: str) -> str:
        response = self.rag_chain.invoke({
            "retrieved_docs": retrieved_docs, 
            "query": query
        })
        return response
    
    def query_traditional(self, query: str) -> Dict:
        try:
            if not self._setup_successful:
                return {"error": "Traditional RAG not available or not setup"}
            
            results = self.retrieval(query)
            retrieved_docs = results.get("documents", [[]])[0]
            
            if not retrieved_docs:
                return {"error": "No relevant documents found"}
            
            response = self._run_rag_chain(retrieved_docs, query)
            
            return {
                "response": response,
                "method": "Traditional RAG",
                "num_docs_retrieved": len(retrieved_docs)
            }
            
        except Exception as e:
            logger.error(f"Error in traditional RAG query: {e}")
            return {"error": f"Traditional RAG search error: {str(e)}"}
    
    def get_document_count(self) -> int:
        try:
            if self.collection:
                return self.collection.count()
            return 0
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0
    
    def is_available(self) -> bool:
        return (TRADITIONAL_RAG_AVAILABLE and 
                self._setup_successful and
                self.rag_chain is not None and 
                self.collection is not None)

if __name__ == "__main__":
    client = TraditionalRAGClient()
    if client.is_available():
        query = "Whats api gateway?"
        result = client.query_traditional(query)
        print(result)
    else:
        print("Traditional RAG client is not available.")