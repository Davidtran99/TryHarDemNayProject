"""
FAISS index management for fast vector similarity search.
"""
import os
import pickle
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

from django.conf import settings


# Default index directory
INDEX_DIR = Path(settings.BASE_DIR) / "artifacts" / "faiss_indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


class FAISSIndex:
    """FAISS index wrapper for vector similarity search."""
    
    def __init__(self, dimension: int, index_type: str = "IVF"):
        """
        Initialize FAISS index.
        
        Args:
            dimension: Embedding dimension.
            index_type: Type of index ('IVF', 'HNSW', 'Flat').
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.id_to_index = {}  # Map object ID to FAISS index
        self.index_to_id = {}  # Reverse mapping
        self._build_index()
    
    def _build_index(self):
        """Build FAISS index based on type."""
        if self.index_type == "Flat":
            # Brute-force exact search
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "IVF":
            # Inverted file index (approximate, faster)
            nlist = 100  # Number of clusters
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        elif self.index_type == "HNSW":
            # Hierarchical Navigable Small World (fast approximate)
            M = 32  # Number of connections
            self.index = faiss.IndexHNSWFlat(self.dimension, M)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")
    
    def train(self, vectors: np.ndarray):
        """Train index (required for IVF)."""
        if hasattr(self.index, 'train') and not self.index.is_trained:
            self.index.train(vectors)
    
    def add(self, vectors: np.ndarray, ids: List[int]):
        """
        Add vectors to index.
        
        Args:
            vectors: Numpy array of shape (n, dimension).
            ids: List of object IDs corresponding to vectors.
        """
        if len(vectors) == 0:
            return
        
        # Normalize vectors
        faiss.normalize_L2(vectors)
        
        # Train if needed (for IVF)
        if hasattr(self.index, 'train') and not self.index.is_trained:
            self.train(vectors)
        
        # Get current index size
        start_idx = len(self.id_to_index)
        
        # Add to index
        self.index.add(vectors)
        
        # Update mappings
        for i, obj_id in enumerate(ids):
            faiss_idx = start_idx + i
            self.id_to_index[obj_id] = faiss_idx
            self.index_to_id[faiss_idx] = obj_id
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector of shape (dimension,).
            k: Number of results to return.
        
        Returns:
            List of (object_id, distance) tuples.
        """
        if self.index.ntotal == 0:
            return []
        
        # Normalize query
        query_vector = query_vector.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_vector)
        
        # Search
        distances, indices = self.index.search(query_vector, k)
        
        # Convert to object IDs
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0:  # Invalid index
                continue
            obj_id = self.index_to_id.get(idx)
            if obj_id is not None:
                # Convert L2 distance to similarity (1 - normalized distance)
                similarity = 1.0 / (1.0 + float(dist))
                results.append((obj_id, similarity))
        
        return results
    
    def save(self, filepath: Path):
        """Save index to file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(filepath))
        
        # Save mappings
        mappings_file = filepath.with_suffix('.mappings.pkl')
        with open(mappings_file, 'wb') as f:
            pickle.dump({
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id,
                'dimension': self.dimension,
                'index_type': self.index_type
            }, f)
    
    @classmethod
    def load(cls, filepath: Path) -> 'FAISSIndex':
        """Load index from file."""
        if not filepath.exists():
            raise FileNotFoundError(f"Index file not found: {filepath}")
        
        # Load FAISS index
        index = faiss.read_index(str(filepath))
        
        # Load mappings
        mappings_file = filepath.with_suffix('.mappings.pkl')
        with open(mappings_file, 'rb') as f:
            mappings = pickle.load(f)
        
        # Create instance
        instance = cls.__new__(cls)
        instance.index = index
        instance.id_to_index = mappings['id_to_index']
        instance.index_to_id = mappings['index_to_id']
        instance.dimension = mappings['dimension']
        instance.index_type = mappings['index_type']
        
        return instance


def build_faiss_index_for_model(model_class, model_name: str, index_type: str = "IVF") -> Optional[FAISSIndex]:
    """
    Build FAISS index for a Django model.
    
    Args:
        model_class: Django model class.
        model_name: Name of model (for file naming).
        index_type: Type of FAISS index.
    
    Returns:
        FAISSIndex instance or None if error.
    """
    if not FAISS_AVAILABLE:
        print("FAISS not available. Skipping index build.")
        return None
    
    from hue_portal.core.embeddings import get_embedding_dimension
    from hue_portal.core.embedding_utils import load_embedding
    
    # Get embedding dimension
    dim = get_embedding_dimension()
    if dim == 0:
        print("Cannot determine embedding dimension. Skipping index build.")
        return None
    
    # Get all instances with embeddings first to determine count
    instances = list(model_class.objects.exclude(embedding__isnull=True))
    if not instances:
        print(f"No instances with embeddings found for {model_name}.")
        return None
    
    # Auto-adjust index type: IVF requires at least 100 vectors for training with 100 clusters
    # If we have fewer vectors, use Flat index instead
    if index_type == "IVF" and len(instances) < 100:
        print(f"⚠️ Only {len(instances)} instances found. Switching from IVF to Flat index (IVF requires >= 100 vectors).")
        index_type = "Flat"
    
    # Create index
    faiss_index = FAISSIndex(dimension=dim, index_type=index_type)
    
    print(f"Building FAISS index for {model_name} ({len(instances)} instances, type: {index_type})...")
    
    # Collect vectors and IDs
    vectors = []
    ids = []
    
    for instance in instances:
        embedding = load_embedding(instance)
        if embedding is not None:
            vectors.append(embedding)
            ids.append(instance.id)
    
    if not vectors:
        print(f"No valid embeddings found for {model_name}.")
        return None
    
    # Convert to numpy array
    vectors_array = np.array(vectors, dtype='float32')
    
    # Add to index
    faiss_index.add(vectors_array, ids)
    
    # Save index
    index_file = INDEX_DIR / f"{model_name.lower()}_{index_type.lower()}.faiss"
    faiss_index.save(index_file)
    
    print(f"✅ Built and saved FAISS index: {index_file}")
    return faiss_index

