"""
Configuration for hybrid search weights and thresholds.
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search."""
    bm25_weight: float = 0.4
    vector_weight: float = 0.6
    min_hybrid_score: float = 0.1
    min_bm25_score: float = 0.0
    min_vector_score: float = 0.1
    top_k_multiplier: int = 2  # Get more results before filtering


# Default configuration
DEFAULT_CONFIG = HybridSearchConfig()

# Per-content-type configurations
CONTENT_TYPE_CONFIGS: Dict[str, HybridSearchConfig] = {
    "procedure": HybridSearchConfig(
        bm25_weight=0.5,
        vector_weight=0.5,
        min_hybrid_score=0.15
    ),
    "fine": HybridSearchConfig(
        bm25_weight=0.7,
        vector_weight=0.3,
        min_hybrid_score=0.08
    ),
    "office": HybridSearchConfig(
        bm25_weight=0.3,
        vector_weight=0.7,
        min_hybrid_score=0.12
    ),
    "advisory": HybridSearchConfig(
        bm25_weight=0.4,
        vector_weight=0.6,
        min_hybrid_score=0.1
    ),
}


def get_config(content_type: str = None) -> HybridSearchConfig:
    """
    Get hybrid search configuration for content type.
    
    Args:
        content_type: Type of content ('procedure', 'fine', 'office', 'advisory').
    
    Returns:
        HybridSearchConfig instance.
    """
    if content_type and content_type in CONTENT_TYPE_CONFIGS:
        return CONTENT_TYPE_CONFIGS[content_type]
    return DEFAULT_CONFIG

