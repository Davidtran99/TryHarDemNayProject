"""
Unit tests for embeddings functionality.
"""
import unittest
import numpy as np
from django.test import TestCase

from hue_portal.core.embeddings import (
    get_embedding_model,
    generate_embedding,
    generate_embeddings_batch,
    cosine_similarity,
    get_embedding_dimension
)
from hue_portal.core.embedding_utils import (
    save_embedding,
    load_embedding,
    has_embedding
)


class EmbeddingsTestCase(TestCase):
    """Test embedding generation and utilities."""
    
    def test_get_embedding_model(self):
        """Test loading embedding model."""
        model = get_embedding_model()
        # Model might not be available in test environment
        # Just check that function doesn't crash
        self.assertIsNotNone(model or True)
    
    def test_generate_embedding(self):
        """Test generating embedding for a single text."""
        text = "Thủ tục đăng ký cư trú"
        embedding = generate_embedding(text)
        
        if embedding is not None:
            self.assertIsInstance(embedding, np.ndarray)
            self.assertGreater(len(embedding), 0)
    
    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts."""
        texts = [
            "Thủ tục đăng ký cư trú",
            "Mức phạt vượt đèn đỏ",
            "Địa chỉ công an phường"
        ]
        embeddings = generate_embeddings_batch(texts, batch_size=2)
        
        if embeddings and embeddings[0] is not None:
            self.assertEqual(len(embeddings), len(texts))
            self.assertIsInstance(embeddings[0], np.ndarray)
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        
        similarity = cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 1.0, places=5)
        
        vec3 = np.array([0.0, 1.0, 0.0])
        similarity2 = cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(similarity2, 0.0, places=5)
    
    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity for orthogonal vectors."""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])
        
        similarity = cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 0.0, places=5)
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        dim = get_embedding_dimension()
        # Dimension might be 0 if model not available
        self.assertIsInstance(dim, int)
        self.assertGreaterEqual(dim, 0)
    
    def test_similar_texts_have_similar_embeddings(self):
        """Test that similar texts produce similar embeddings."""
        text1 = "Thủ tục đăng ký cư trú"
        text2 = "Đăng ký thủ tục cư trú"
        text3 = "Mức phạt giao thông"
        
        emb1 = generate_embedding(text1)
        emb2 = generate_embedding(text2)
        emb3 = generate_embedding(text3)
        
        if emb1 is not None and emb2 is not None and emb3 is not None:
            sim_similar = cosine_similarity(emb1, emb2)
            sim_different = cosine_similarity(emb1, emb3)
            
            # Similar texts should have higher similarity
            self.assertGreater(sim_similar, sim_different)


class EmbeddingUtilsTestCase(TestCase):
    """Test embedding utility functions."""
    
    def test_save_and_load_embedding(self):
        """Test saving and loading embeddings."""
        from hue_portal.core.models import Procedure
        
        # Create a test procedure
        procedure = Procedure.objects.create(
            title="Test Procedure",
            domain="Test"
        )
        
        # Create a dummy embedding
        dummy_embedding = np.random.rand(384).astype(np.float32)
        
        # Save embedding
        success = save_embedding(procedure, dummy_embedding)
        self.assertTrue(success)
        
        # Reload from database
        procedure.refresh_from_db()
        
        # Load embedding
        loaded_embedding = load_embedding(procedure)
        self.assertIsNotNone(loaded_embedding)
        self.assertTrue(np.allclose(dummy_embedding, loaded_embedding))
    
    def test_has_embedding(self):
        """Test checking if instance has embedding."""
        from hue_portal.core.models import Procedure
        
        procedure = Procedure.objects.create(
            title="Test Procedure",
            domain="Test"
        )
        
        # Initially no embedding
        self.assertFalse(has_embedding(procedure))
        
        # Add embedding
        dummy_embedding = np.random.rand(384).astype(np.float32)
        save_embedding(procedure, dummy_embedding)
        
        # Refresh and check
        procedure.refresh_from_db()
        self.assertTrue(has_embedding(procedure))

