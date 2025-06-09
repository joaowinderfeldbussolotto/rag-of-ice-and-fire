import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
        
    # RAG settings
    GRAPHRAG_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    PROJECT_DIRECTORY: str = "../raggraphragtesttest/"
    CHROMA_DB_PATH: str = "../rag/chromadb"
    INPUT_DIRECTORY: str = "../graphragtest/input/"
    
    # Default search parameters
    DEFAULT_COMMUNITY_LEVEL: int = 2
    DEFAULT_RESPONSE_TYPE: str = "Multiple Paragraphs"
    DEFAULT_NUM_RESULTS: int = 5
    
    class Config:
        env_file = "../.env"
        case_sensitive = True

settings = Settings()