import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import official GraphRAG API
try:
    import graphrag.api as api
    from graphrag.config.load_config import load_config
    from graphrag.index.typing.pipeline_run_result import PipelineRunResult
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    GRAPHRAG_AVAILABLE = False
    logger.warning(f"GraphRAG dependencies not available: {e}")

class GraphRAGClient:
    """GraphRAG client using the official GraphRAG API"""
    
    def __init__(self, project_directory: str = "../graphragtest/"):
        self.project_directory = Path(project_directory)
        self.graphrag_config = None
        
        # Data containers (loaded on demand)
        self.entities_df = None
        self.communities_df = None
        self.community_reports_df = None
        self.relationships_df = None
        self.text_units_df = None
        
        # Configuration
        self.community_level = 2
        
        # Auto-setup on initialization
        if GRAPHRAG_AVAILABLE:
            self.setup_config()
            self.load_data()
    
    def setup_config(self) -> bool:
        """Load GraphRAG configuration from project directory"""
        try:
            if not GRAPHRAG_AVAILABLE:
                logger.error("GraphRAG library not available")
                return False
            
            # Load configuration from settings.yaml in project directory
            self.graphrag_config = load_config(self.project_directory)
            
            if self.graphrag_config is None:
                logger.error(f"Could not load GraphRAG config from {self.project_directory}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading GraphRAG config: {str(e)}")
            return False
    
    async def build_index(self) -> Dict:
        """Build GraphRAG index from input data"""
        try:
            if not GRAPHRAG_AVAILABLE or not self.graphrag_config:
                return {"error": "GraphRAG not available or config not loaded"}
            
            # Run the indexing pipeline
            index_result: List[PipelineRunResult] = await api.build_index(
                config=self.graphrag_config
            )
            
            # Process results
            results = []
            errors = []
            
            for workflow_result in index_result:
                if workflow_result.errors:
                    errors.extend(workflow_result.errors)
                    results.append({
                        "workflow": workflow_result.workflow,
                        "status": "error",
                        "errors": workflow_result.errors
                    })
                else:
                    results.append({
                        "workflow": workflow_result.workflow,
                        "status": "success"
                    })
            
            return {
                "success": len(errors) == 0,
                "results": results,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Index building error: {e}")
            return {"error": f"Index building error: {str(e)}"}
    
    def load_data(self) -> bool:
        """Load GraphRAG output data from parquet files"""
        try:
            output_dir = self.project_directory / "output"
            
            if not output_dir.exists():
                logger.error(f"Output directory not found: {output_dir}")
                return False
            
            # Load required files for queries
            entities_file = output_dir / "entities.parquet"
            communities_file = output_dir / "communities.parquet"
            community_reports_file = output_dir / "community_reports.parquet"
            
            if not all([entities_file.exists(), communities_file.exists(), community_reports_file.exists()]):
                logger.error("Required output files not found. Please run indexing first.")
                return False
            
            # Load the data
            self.entities_df = pd.read_parquet(entities_file)
            self.communities_df = pd.read_parquet(communities_file)
            self.community_reports_df = pd.read_parquet(community_reports_file)
            
            # Load optional files
            relationships_file = output_dir / "relationships.parquet"
            if relationships_file.exists():
                self.relationships_df = pd.read_parquet(relationships_file)
            
            text_units_file = output_dir / "text_units.parquet"
            if text_units_file.exists():
                self.text_units_df = pd.read_parquet(text_units_file)
            
            logger.info(f"Loaded data: {len(self.entities_df)} entities, {len(self.communities_df)} communities, {len(self.community_reports_df)} reports")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
    
    async def query_global(self, query: str, community_level: int = None, 
                          response_type: str = "Multiple Paragraphs",
                          dynamic_community_selection: bool = False) -> Dict:
        """Perform a global search using community reports"""
        try:
            if not GRAPHRAG_AVAILABLE or not self.graphrag_config:
                return {"error": "GraphRAG not available or config not loaded"}
            
            if self.entities_df is None or self.communities_df is None or self.community_reports_df is None:
                return {"error": "Data not loaded. Call load_data() first."}
            
            if community_level is None:
                community_level = self.community_level
            
            # Use the official GraphRAG global search API
            response, context = await api.global_search(
                config=self.graphrag_config,
                entities=self.entities_df,
                communities=self.communities_df,
                community_reports=self.community_reports_df,
                community_level=community_level,
                dynamic_community_selection=dynamic_community_selection,
                response_type=response_type,
                query=query,
            )
            
            return {
                "response": response,
                "context": context,
                "community_level": community_level,
                "response_type": response_type,
                "dynamic_community_selection": dynamic_community_selection
            }
            
        except Exception as e:
            logger.error(f"Global search error: {e}")
            return {"error": f"Global search error: {str(e)}"}
        
            
    async def query_local(self, query: str, community_level: int = None,
                         response_type: str = "Multiple Paragraphs") -> Dict:
        """Perform a local search using entities and relationships"""
        try:
            if not GRAPHRAG_AVAILABLE or not self.graphrag_config:
                return {"error": "GraphRAG not available or config not loaded"}
            
            if self.entities_df is None:
                return {"error": "Data not loaded. Call load_data() first."}
            
            if community_level is None:
                community_level = self.community_level
            
            # Load additional data needed for local search
            output_dir = self.project_directory / "output"
            
            # Load all required data for local search
            if self.relationships_df is None:
                relationships_file = output_dir / "relationships.parquet"
                if relationships_file.exists():
                    self.relationships_df = pd.read_parquet(relationships_file)
            
            if self.text_units_df is None:
                text_units_file = output_dir / "text_units.parquet"
                if text_units_file.exists():
                    self.text_units_df = pd.read_parquet(text_units_file)
            
            # Use the official GraphRAG local search API
            response, context = await api.local_search(
                config=self.graphrag_config,
                entities=self.entities_df,
                communities=self.communities_df,
                relationships=self.relationships_df if self.relationships_df is not None else pd.DataFrame(),
                text_units=self.text_units_df if self.text_units_df is not None else pd.DataFrame(),
                community_reports=self.community_reports_df,
                community_level=community_level,
                response_type=response_type,
                covariates=None,
                query=query,
            )
            
            return {
                "response": response,
                "context": context,
                "community_level": community_level,
                "response_type": response_type
            }
            
        except Exception as e:
            logger.error(f"Local search error: {e}")
            return {"error": f"Local search error: {str(e)}"}
    
    async def query_drift(self, query: str, community_level: int = None,
                         response_type: str = "Multiple Paragraphs") -> Dict:
        """Perform a drift search for temporal and contextual analysis"""
        try:
            if not GRAPHRAG_AVAILABLE or not self.graphrag_config:
                return {"error": "GraphRAG not available or config not loaded"}
            
            if self.entities_df is None or self.relationships_df is None:
                return {"error": "Data not loaded or insufficient data for drift analysis"}
            
            if community_level is None:
                community_level = self.community_level
            
            # Load additional data needed for drift search
            output_dir = self.project_directory / "output"
            
            # Ensure all required data is loaded
            if self.text_units_df is None:
                text_units_file = output_dir / "text_units.parquet"
                if text_units_file.exists():
                    self.text_units_df = pd.read_parquet(text_units_file)
            
            # Check if GraphRAG API has drift search capability
            if not hasattr(api, 'drift_search'):
                return {"error": "Drift search not available in current GraphRAG version"}
            
            # Use official drift search
            response, context = await api.drift_search(
                config=self.graphrag_config,
                entities=self.entities_df,
                communities=self.communities_df,
                relationships=self.relationships_df,
                text_units=self.text_units_df if self.text_units_df is not None else pd.DataFrame(),
                community_reports=self.community_reports_df,
                community_level=community_level,
                response_type=response_type,
                query=query,
            )
            
            drift_analysis = self._extract_drift_metadata(context) if context else {}
            
            return {
                "response": response,
                "context": context,
                "community_level": community_level,
                "response_type": response_type,
                "drift_analysis": drift_analysis
            }
            
        except Exception as e:
            logger.error(f"Drift search error: {e}")
            return {"error": f"Drift search error: {str(e)}"}
    
    def _extract_drift_metadata(self, context: Dict) -> Dict:
        """Extract drift-specific metadata from search context"""
        drift_metadata = {
            "temporal_patterns": [],
            "entity_evolution": [],
            "community_shifts": [],
            "relationship_changes": []
        }
        
        try:
            # Extract temporal information if available in context
            if isinstance(context, dict):
                if "temporal_data" in context:
                    drift_metadata["temporal_patterns"] = context["temporal_data"]
                
                if "entity_changes" in context:
                    drift_metadata["entity_evolution"] = context["entity_changes"]
                
                if "community_evolution" in context:
                    drift_metadata["community_shifts"] = context["community_evolution"]
                
                if "relationship_dynamics" in context:
                    drift_metadata["relationship_changes"] = context["relationship_dynamics"]
                    
        except Exception as e:
            logger.warning(f"Error extracting drift metadata: {e}")
        
        return drift_metadata


    
    def get_data_summary(self) -> Dict:
        """Get summary of loaded data"""
        return {
            "entities": len(self.entities_df) if self.entities_df is not None else 0,
            "communities": len(self.communities_df) if self.communities_df is not None else 0,
            "community_reports": len(self.community_reports_df) if self.community_reports_df is not None else 0,
            "relationships": len(self.relationships_df) if self.relationships_df is not None else 0,
            "text_units": len(self.text_units_df) if self.text_units_df is not None else 0,
        }
