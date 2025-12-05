"""
Unit tests for Pure Semantic Search.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.db.models import QuerySet
from hue_portal.core.pure_semantic_search import (
    get_vector_scores,
    parallel_vector_search,
    pure_semantic_search,
    calculate_exact_match_boost
)


class TestPureSemanticSearch(unittest.TestCase):
    """Test Pure Semantic Search functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_queryset = Mock(spec=QuerySet)
        self.mock_queryset.__iter__ = Mock(return_value=iter([]))
        self.mock_queryset.__len__ = Mock(return_value=0)
    
    @patch('hue_portal.core.pure_semantic_search.get_embedding_model')
    @patch('hue_portal.core.pure_semantic_search.generate_embedding')
    @patch('hue_portal.core.pure_semantic_search.load_embedding')
    @patch('hue_portal.core.pure_semantic_search.cosine_similarity')
    def test_get_vector_scores(self, mock_cosine, mock_load, mock_gen, mock_model):
        """Test get_vector_scores function."""
        # Mock embedding model
        mock_model.return_value = Mock()
        mock_gen.return_value = [0.1] * 1024  # BGE-M3 dimension
        mock_cosine.return_value = 0.8
        
        # Mock objects with embeddings
        obj1 = Mock()
        obj2 = Mock()
        mock_load.side_effect = [[0.1] * 1024, [0.1] * 1024]
        
        self.mock_queryset.__iter__ = Mock(return_value=iter([obj1, obj2]))
        self.mock_queryset.__len__ = Mock(return_value=2)
        
        results = get_vector_scores(self.mock_queryset, "test query", top_k=10)
        
        self.assertIsInstance(results, list)
        # Should return results with scores
        if results:
            self.assertIsInstance(results[0], tuple)
            self.assertEqual(len(results[0]), 2)
    
    def test_calculate_exact_match_boost(self):
        """Test exact match boost calculation."""
        obj = Mock()
        obj.title = "Quy định điều 12"
        obj.name = "Điều 12"
        
        # Test phrase match
        boost = calculate_exact_match_boost(obj, "điều 12", ["title", "name"])
        self.assertGreater(boost, 0.0)
        self.assertLessEqual(boost, 1.0)
        
        # Test no match
        boost2 = calculate_exact_match_boost(obj, "điều 99", ["title", "name"])
        self.assertLess(boost2, boost)
    
    @patch('hue_portal.core.pure_semantic_search.get_vector_scores')
    def test_parallel_vector_search_single_query(self, mock_get_scores):
        """Test parallel_vector_search with single query."""
        obj1 = Mock()
        obj2 = Mock()
        mock_get_scores.return_value = [(obj1, 0.9), (obj2, 0.8)]
        
        self.mock_queryset.__iter__ = Mock(return_value=iter([obj1, obj2]))
        
        results = parallel_vector_search(
            ["test query"],
            self.mock_queryset,
            top_k_per_query=5,
            final_top_k=2
        )
        
        self.assertIsInstance(results, list)
        # Should use single query search path
    
    @patch('hue_portal.core.pure_semantic_search.get_vector_scores')
    def test_parallel_vector_search_multiple_queries(self, mock_get_scores):
        """Test parallel_vector_search with multiple queries."""
        obj1 = Mock()
        obj2 = Mock()
        obj3 = Mock()
        
        # Different results for different queries
        mock_get_scores.side_effect = [
            [(obj1, 0.9), (obj2, 0.8)],  # Query 1
            [(obj2, 0.85), (obj3, 0.75)],  # Query 2
        ]
        
        self.mock_queryset.__iter__ = Mock(return_value=iter([obj1, obj2, obj3]))
        
        results = parallel_vector_search(
            ["query 1", "query 2"],
            self.mock_queryset,
            top_k_per_query=5,
            final_top_k=3
        )
        
        self.assertIsInstance(results, list)
        # Should merge results from multiple queries
        # obj2 should appear with max score (0.85)
    
    @patch('hue_portal.core.pure_semantic_search.parallel_vector_search')
    def test_pure_semantic_search_single(self, mock_parallel):
        """Test pure_semantic_search with single query."""
        obj1 = Mock()
        obj2 = Mock()
        mock_parallel.return_value = [(obj1, 0.9), (obj2, 0.8)]
        
        results = pure_semantic_search(
            ["test query"],
            self.mock_queryset,
            top_k=2
        )
        
        self.assertIsInstance(results, list)
        # Should return objects only (without scores)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], obj1)
        self.assertEqual(results[1], obj2)
    
    @patch('hue_portal.core.pure_semantic_search.parallel_vector_search')
    def test_pure_semantic_search_multiple(self, mock_parallel):
        """Test pure_semantic_search with multiple queries."""
        obj1 = Mock()
        obj2 = Mock()
        mock_parallel.return_value = [(obj1, 0.9), (obj2, 0.8)]
        
        results = pure_semantic_search(
            ["query 1", "query 2", "query 3"],
            self.mock_queryset,
            top_k=2
        )
        
        self.assertIsInstance(results, list)
        # Should use parallel_vector_search
        mock_parallel.assert_called_once()
    
    def test_pure_semantic_search_empty_queries(self):
        """Test pure_semantic_search with empty queries."""
        results = pure_semantic_search([], self.mock_queryset, top_k=10)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()

