"""
Fast Path Handler - Returns cached responses from golden dataset.
"""
from typing import Dict, Any
from hue_portal.core.models import GoldenQuery


class FastPathHandler:
    """Handle Fast Path queries using golden dataset."""
    
    def handle(self, query: str, golden_query_id: int) -> Dict[str, Any]:
        """
        Get cached response from golden dataset.
        
        Args:
            query: User query (for logging).
            golden_query_id: ID of matched golden query.
        
        Returns:
            Response dict (same format as Slow Path) with additional metadata.
        """
        try:
            golden_query = GoldenQuery.objects.get(id=golden_query_id, is_active=True)
        except GoldenQuery.DoesNotExist:
            # Fallback: return error response
            return {
                "message": "Xin lỗi, không tìm thấy thông tin trong cơ sở dữ liệu.",
                "intent": "error",
                "results": [],
                "count": 0,
                "_source": "fast_path",
                "_error": "golden_query_not_found"
            }
        
        # Increment usage count (async update for performance)
        golden_query.usage_count += 1
        golden_query.save(update_fields=['usage_count'])
        
        # Return cached response
        response = golden_query.response_data.copy()
        
        # Add metadata
        response['_source'] = 'fast_path'
        response['_golden_query_id'] = golden_query_id
        response['_verified_by'] = golden_query.verified_by
        response['_accuracy_score'] = golden_query.accuracy_score
        
        # Ensure required fields exist
        if 'message' not in response:
            response['message'] = golden_query.response_message
        
        if 'intent' not in response:
            response['intent'] = golden_query.intent
        
        if 'count' not in response:
            response['count'] = len(response.get('results', []))
        
        return response

