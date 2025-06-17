import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# GraphRAG imports with better error handling
try:
    import graphrag.api as api
    from graphrag.config.load_config import load_config
    from graphrag.index.typing.pipeline_run_result import PipelineRunResult
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    GRAPHRAG_AVAILABLE = False
    logger.warning(f"GraphRAG not available: {e}")

def require_graphrag(func):
    """Decorator to ensure GraphRAG is available"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not GRAPHRAG_AVAILABLE:
            return {"error": "GraphRAG library not installed"}
        if not self.graphrag_config:
            return {"error": "GraphRAG config not loaded"}
        return func(self, *args, **kwargs)
    return wrapper

def require_data(func):
    """Decorator to ensure data is loaded"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._has_required_data():
            return {"error": "Required data not loaded. Run load_data() first"}
        return func(self, *args, **kwargs)
    return wrapper

class GraphRAGClient:
    """Simplified GraphRAG client with better error handling and validation"""
    
    # Class-level constants
    DEFAULT_RESPONSE_TYPE = "Multiple Paragraphs"
    DEFAULT_COMMUNITY_LEVEL = 2
    
    def __init__(self, project_directory: str = "./graphragtest/"):
        self.project_directory = Path(project_directory)
        self.graphrag_config = None
        self.community_level = self.DEFAULT_COMMUNITY_LEVEL
        
        # Data storage - using None to indicate not loaded
        self._data = {
            'entities': None,
            'communities': None, 
            'community_reports': None,
            'relationships': None,
            'text_units': None
        }
        
        # Auto-initialize if possible
        if GRAPHRAG_AVAILABLE:
            self.setup_config()
            self.load_data()
    
    @property
    def output_dir(self) -> Path:
        """Get output directory path"""
        return self.project_directory / "output"
    
    def _has_required_data(self) -> bool:
        """Check if minimum required data is loaded"""
        required = ['entities', 'communities', 'community_reports']
        return all(self._data[key] is not None for key in required)
    
    def _load_parquet_safe(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Safely load parquet file with error handling"""
        try:
            if file_path.exists():
                return pd.read_parquet(file_path)
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
        return None
    
    def setup_config(self) -> bool:
        """Load GraphRAG configuration"""
        if not GRAPHRAG_AVAILABLE:
            logger.error("GraphRAG not available")
            return False
        
        try:
            self.graphrag_config = load_config(self.project_directory)
            if self.graphrag_config is None:
                logger.error(f"No valid config found in {self.project_directory}")
                return False
            return True
        except Exception as e:
            logger.error(f"Config loading failed: {e}")
            return False
    
    def load_data(self) -> bool:
        """Load all available GraphRAG output data"""
        if not self.output_dir.exists():
            logger.error(f"Output directory not found: {self.output_dir}")
            return False
        
        # Define file mappings
        files = {
            'entities': 'entities.parquet',
            'communities': 'communities.parquet',
            'community_reports': 'community_reports.parquet',
            'relationships': 'relationships.parquet',
            'text_units': 'text_units.parquet'
        }
        
        # Load each file
        loaded_count = 0
        for key, filename in files.items():
            file_path = self.output_dir / filename
            df = self._load_parquet_safe(file_path)
            self._data[key] = df
            if df is not None:
                loaded_count += 1
        
        if loaded_count == 0:
            logger.error("No data files could be loaded")
            return False
        
        # Check for minimum required files
        if not self._has_required_data():
            logger.error("Missing required files: entities, communities, or community_reports")
            return False
        
        logger.info(f"Loaded {loaded_count}/5 data files successfully")
        return True
    
    @require_graphrag
    async def build_index(self) -> Dict:
        """Build GraphRAG index with simplified result processing"""
        try:
            results = await api.build_index(config=self.graphrag_config)
            
            success_count = 0
            all_errors = []
            
            for result in results:
                if result.errors:
                    all_errors.extend(result.errors)
                else:
                    success_count += 1
            
            return {
                "success": len(all_errors) == 0,
                "workflows_completed": success_count,
                "total_workflows": len(results),
                "errors": all_errors
            }
            
        except Exception as e:
            logger.error(f"Index building failed: {e}")
            return {"error": str(e)}
    
    @require_graphrag
    @require_data
    async def query_global(self, query: str, 
                          community_level: Optional[int] = None,
                          response_type: str = DEFAULT_RESPONSE_TYPE,
                          dynamic_community_selection: bool = False) -> Dict:
        """Global search using community reports"""
        try:
            level = community_level or self.community_level
            
            response, context = await api.global_search(
                config=self.graphrag_config,
                entities=self._data['entities'],
                communities=self._data['communities'],
                community_reports=self._data['community_reports'],
                community_level=level,
                dynamic_community_selection=dynamic_community_selection,
                response_type=response_type,
                query=query,
            )
            
            return {
                "response": response,
                "context": context,
                "query_params": {
                    "community_level": level,
                    "response_type": response_type,
                    "dynamic_selection": dynamic_community_selection
                }
            }
            
        except Exception as e:
            logger.error(f"Global search failed: {e}")
            return {"error": str(e)}
    
    @require_graphrag 
    @require_data
    async def query_local(self, query: str,
                         community_level: Optional[int] = None,
                         response_type: str = DEFAULT_RESPONSE_TYPE) -> Dict:
        """Local search using entities and relationships"""
        try:
            level = community_level or self.community_level
            
            # Handle DataFrame parameters safely
            relationships_df = self._data['relationships'] if self._data['relationships'] is not None else pd.DataFrame()
            text_units_df = self._data['text_units'] if self._data['text_units'] is not None else pd.DataFrame()
            
            response, context = await api.local_search(
                config=self.graphrag_config,
                entities=self._data['entities'],
                communities=self._data['communities'],
                relationships=relationships_df,
                text_units=text_units_df,
                community_reports=self._data['community_reports'],
                community_level=level,
                response_type=response_type,
                covariates=None,
                query=query,
            )
            
            return {
                "response": response,
                "context": context,
                "query_params": {
                    "community_level": level,
                    "response_type": response_type
                }
            }
            
        except Exception as e:
            logger.error(f"Local search failed: {e}")
            return {"error": str(e)}
    
    @require_graphrag
    @require_data 
    async def query_drift(self, query: str,
                         community_level: Optional[int] = None,
                         response_type: str = DEFAULT_RESPONSE_TYPE) -> Dict:
        """Drift search for temporal analysis (if available)"""
        if not hasattr(api, 'drift_search'):
            return {"error": "Drift search not available in current GraphRAG version"}
        
        if self._data['relationships'] is None:
            return {"error": "Relationships data required for drift analysis"}
        
        try:
            level = community_level or self.community_level
            
            # Handle DataFrame parameters safely
            text_units_df = self._data['text_units'] if self._data['text_units'] is not None else pd.DataFrame()
            
            response, context = await api.drift_search(
                config=self.graphrag_config,
                entities=self._data['entities'],
                communities=self._data['communities'],
                relationships=self._data['relationships'],
                text_units=text_units_df,
                community_reports=self._data['community_reports'],
                community_level=level,
                response_type=response_type,
                query=query,
            )
            
            return {
                "response": response,
                "context": context,
                "query_params": {
                    "community_level": level,
                    "response_type": response_type
                }
            }
            
        except Exception as e:
            logger.error(f"Drift search failed: {e}")
            return {"error": str(e)}
    
    def get_status(self) -> Dict:
        """Get comprehensive client status"""
        data_summary = {k: len(v) if v is not None else 0 
                       for k, v in self._data.items()}
        
        return {
            "graphrag_available": GRAPHRAG_AVAILABLE,
            "config_loaded": self.graphrag_config is not None,
            "data_loaded": self._has_required_data(),
            "project_directory": str(self.project_directory),
            "output_directory_exists": self.output_dir.exists(),
            "data_summary": data_summary,
            "community_level": self.community_level
        }
    
    def get_data_summary(self) -> Dict:
        """Get summary of loaded data (backwards compatibility)"""
        return self.get_status()["data_summary"]
    
    @contextmanager
    def temp_community_level(self, level: int):
        """Temporarily change community level"""
        old_level = self.community_level
        self.community_level = level
        try:
            yield
        finally:
            self.community_level = old_level