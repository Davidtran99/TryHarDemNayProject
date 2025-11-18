"""
Utility functions for loading and working with stored embeddings.
"""
import pickle
from typing import Optional
import numpy as np
from django.db import models


def save_embedding(instance: models.Model, embedding: np.ndarray) -> bool:
    """
    Save embedding to model instance.
    
    Args:
        instance: Django model instance.
        embedding: Numpy array of embedding.
    
    Returns:
        True if successful, False otherwise.
    """
    if embedding is None:
        return False
    
    try:
        embedding_binary = pickle.dumps(embedding)
        instance.embedding = embedding_binary
        instance.save(update_fields=['embedding'])
        return True
    except Exception as e:
        print(f"Error saving embedding: {e}")
        return False


def load_embedding(instance: models.Model) -> Optional[np.ndarray]:
    """
    Load embedding from model instance.
    
    Args:
        instance: Django model instance with embedding field.
    
    Returns:
        Numpy array of embedding or None if not available.
    """
    if not hasattr(instance, 'embedding') or instance.embedding is None:
        return None
    
    try:
        embedding = pickle.loads(instance.embedding)
        return embedding
    except Exception as e:
        print(f"Error loading embedding: {e}")
        return None


def has_embedding(instance: models.Model) -> bool:
    """
    Check if instance has an embedding.
    
    Args:
        instance: Django model instance.
    
    Returns:
        True if embedding exists, False otherwise.
    """
    return hasattr(instance, 'embedding') and instance.embedding is not None

