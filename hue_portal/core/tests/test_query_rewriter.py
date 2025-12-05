"""
Unit tests for Query Rewriter.
"""
import unittest
from unittest.mock import Mock, patch
from hue_portal.core.query_rewriter import QueryRewriter, get_query_rewriter


class TestQueryRewriter(unittest.TestCase):
    """Test QueryRewriter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.llm_generator = Mock()
        self.llm_generator.is_available.return_value = True
        self.llm_generator._generate_from_prompt.return_value = '{"queries": ["nội dung điều 12", "quy định điều 12", "điều 12 quy định về"]}'
        self.llm_generator._extract_json_payload.return_value = {
            "queries": ["nội dung điều 12", "quy định điều 12", "điều 12 quy định về"]
        }
        self.rewriter = QueryRewriter(llm_generator=self.llm_generator)
    
    def test_rewrite_query_with_llm(self):
        """Test query rewriting with LLM."""
        queries = self.rewriter.rewrite_query("điều 12 nói gì")
        
        self.assertIsInstance(queries, list)
        self.assertGreaterEqual(len(queries), 3)
        self.assertLessEqual(len(queries), 5)
        self.assertTrue(all(isinstance(q, str) for q in queries))
        
        # Verify LLM was called
        self.llm_generator._generate_from_prompt.assert_called_once()
    
    def test_rewrite_query_fallback(self):
        """Test query rewriting fallback when LLM is not available."""
        self.llm_generator.is_available.return_value = False
        rewriter = QueryRewriter(llm_generator=self.llm_generator)
        
        queries = rewriter.rewrite_query("điều 12 nói gì")
        
        self.assertIsInstance(queries, list)
        self.assertGreaterEqual(len(queries), 3)
        self.assertLessEqual(len(queries), 5)
        # Should include original query
        self.assertIn("điều 12 nói gì", queries)
    
    def test_rewrite_query_empty(self):
        """Test query rewriting with empty query."""
        queries = self.rewriter.rewrite_query("")
        self.assertEqual(queries, [])
        
        queries = self.rewriter.rewrite_query("   ")
        self.assertEqual(queries, [])
    
    def test_rewrite_query_with_context(self):
        """Test query rewriting with conversation context."""
        context = [
            {"role": "user", "content": "Tôi muốn hỏi về kỷ luật"},
            {"role": "bot", "content": "Bạn muốn hỏi về vấn đề gì?"},
        ]
        
        queries = self.rewriter.rewrite_query("điều 12", context=context)
        
        self.assertIsInstance(queries, list)
        self.assertGreaterEqual(len(queries), 3)
        # Verify context was passed to LLM
        call_args = self.llm_generator._generate_from_prompt.call_args[0][0]
        self.assertIn("điều 12", call_args)
    
    def test_get_cache_key(self):
        """Test cache key generation."""
        key1 = self.rewriter.get_cache_key("điều 12 nói gì")
        key2 = self.rewriter.get_cache_key("điều 12 nói gì")
        key3 = self.rewriter.get_cache_key("điều 13 nói gì")
        
        # Same query should generate same key
        self.assertEqual(key1, key2)
        # Different query should generate different key
        self.assertNotEqual(key1, key3)
    
    def test_get_cache_key_with_context(self):
        """Test cache key generation with context."""
        context = [{"role": "user", "content": "test"}]
        key1 = self.rewriter.get_cache_key("điều 12", context=context)
        key2 = self.rewriter.get_cache_key("điều 12", context=context)
        key3 = self.rewriter.get_cache_key("điều 12", context=None)
        
        # Same query + context should generate same key
        self.assertEqual(key1, key2)
        # Different context should generate different key
        self.assertNotEqual(key1, key3)
    
    def test_fallback_patterns(self):
        """Test fallback rewrite patterns."""
        self.llm_generator.is_available.return_value = False
        rewriter = QueryRewriter(llm_generator=self.llm_generator)
        
        # Test "điều" pattern
        queries = rewriter.rewrite_query("điều 12")
        self.assertGreater(len(queries), 1)
        
        # Test "phạt" pattern
        queries = rewriter.rewrite_query("mức phạt vi phạm")
        self.assertGreater(len(queries), 1)
        self.assertTrue(any("phạt" in q.lower() for q in queries))
    
    def test_get_query_rewriter(self):
        """Test get_query_rewriter function."""
        rewriter = get_query_rewriter()
        self.assertIsInstance(rewriter, QueryRewriter)
        
        rewriter2 = get_query_rewriter(self.llm_generator)
        self.assertIsInstance(rewriter2, QueryRewriter)


if __name__ == "__main__":
    unittest.main()

