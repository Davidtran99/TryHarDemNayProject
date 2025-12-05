"""
Analytics and monitoring for Dual-Path RAG routing.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.db.models import Count, Avg, Q, F
from django.utils import timezone

from hue_portal.core.models import QueryRoutingLog, GoldenQuery


def get_routing_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get routing statistics for the last N days.
    
    Args:
        days: Number of days to analyze (default: 7).
    
    Returns:
        Dictionary with routing statistics.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    logs = QueryRoutingLog.objects.filter(created_at__gte=cutoff_date)
    
    total_count = logs.count()
    if total_count == 0:
        return {
            'total_queries': 0,
            'fast_path_count': 0,
            'slow_path_count': 0,
            'fast_path_percentage': 0.0,
            'slow_path_percentage': 0.0,
            'fast_path_avg_time_ms': 0.0,
            'slow_path_avg_time_ms': 0.0,
            'router_methods': {},
            'intent_breakdown': {},
            'cache_hit_rate': 0.0,
            'top_golden_queries': [],
        }
    
    # Path statistics
    fast_path_count = logs.filter(route='fast_path').count()
    slow_path_count = logs.filter(route='slow_path').count()
    
    # Average response times
    fast_path_avg = logs.filter(route='fast_path').aggregate(
        avg_time=Avg('response_time_ms')
    )['avg_time'] or 0.0
    
    slow_path_avg = logs.filter(route='slow_path').aggregate(
        avg_time=Avg('response_time_ms')
    )['avg_time'] or 0.0
    
    # Router methods breakdown
    router_methods = dict(
        logs.values('router_method')
        .annotate(count=Count('id'))
        .values_list('router_method', 'count')
    )
    
    # Intent breakdown
    intent_breakdown = dict(
        logs.values('intent')
        .annotate(count=Count('id'))
        .values_list('intent', 'count')
    )
    
    # Cache hit rate (Fast Path usage)
    cache_hit_rate = (fast_path_count / total_count * 100) if total_count > 0 else 0.0
    
    # Top golden queries by usage
    top_golden_queries = list(
        GoldenQuery.objects.filter(is_active=True)
        .order_by('-usage_count')[:10]
        .values('id', 'query', 'intent', 'usage_count', 'accuracy_score')
    )
    
    return {
        'total_queries': total_count,
        'fast_path_count': fast_path_count,
        'slow_path_count': slow_path_count,
        'fast_path_percentage': (fast_path_count / total_count * 100) if total_count > 0 else 0.0,
        'slow_path_percentage': (slow_path_count / total_count * 100) if total_count > 0 else 0.0,
        'fast_path_avg_time_ms': round(fast_path_avg, 2),
        'slow_path_avg_time_ms': round(slow_path_avg, 2),
        'router_methods': router_methods,
        'intent_breakdown': intent_breakdown,
        'cache_hit_rate': round(cache_hit_rate, 2),
        'top_golden_queries': top_golden_queries,
        'period_days': days,
    }


def get_golden_dataset_stats() -> Dict[str, Any]:
    """
    Get statistics about the golden dataset.
    
    Returns:
        Dictionary with golden dataset statistics.
    """
    total_queries = GoldenQuery.objects.count()
    active_queries = GoldenQuery.objects.filter(is_active=True).count()
    
    # Intent breakdown
    intent_breakdown = dict(
        GoldenQuery.objects.filter(is_active=True)
        .values('intent')
        .annotate(count=Count('id'))
        .values_list('intent', 'count')
    )
    
    # Total usage
    total_usage = GoldenQuery.objects.aggregate(
        total_usage=Count('usage_count')
    )['total_usage'] or 0
    
    # Average accuracy
    avg_accuracy = GoldenQuery.objects.filter(is_active=True).aggregate(
        avg_accuracy=Avg('accuracy_score')
    )['avg_accuracy'] or 1.0
    
    # Queries with embeddings
    with_embeddings = GoldenQuery.objects.filter(
        is_active=True,
        query_embedding__isnull=False
    ).count()
    
    return {
        'total_queries': total_queries,
        'active_queries': active_queries,
        'intent_breakdown': intent_breakdown,
        'total_usage': total_usage,
        'avg_accuracy': round(avg_accuracy, 3),
        'with_embeddings': with_embeddings,
        'embedding_coverage': (with_embeddings / active_queries * 100) if active_queries > 0 else 0.0,
    }


def get_performance_metrics(days: int = 7) -> Dict[str, Any]:
    """
    Get performance metrics for both paths.
    
    Args:
        days: Number of days to analyze.
    
    Returns:
        Dictionary with performance metrics.
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    logs = QueryRoutingLog.objects.filter(created_at__gte=cutoff_date)
    
    # P95, P99 response times
    fast_path_times = list(
        logs.filter(route='fast_path')
        .values_list('response_time_ms', flat=True)
        .order_by('response_time_ms')
    )
    slow_path_times = list(
        logs.filter(route='slow_path')
        .values_list('response_time_ms', flat=True)
        .order_by('response_time_ms')
    )
    
    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile of sorted data."""
        if not data:
            return 0.0
        if len(data) == 1:
            return data[0]
        k = (len(data) - 1) * p
        f = int(k)
        c = k - f
        if f + 1 < len(data):
            return float(data[f] + c * (data[f + 1] - data[f]))
        return float(data[-1])
    
    return {
        'fast_path': {
            'p50': percentile(fast_path_times, 0.5),
            'p95': percentile(fast_path_times, 0.95),
            'p99': percentile(fast_path_times, 0.99),
            'min': min(fast_path_times) if fast_path_times else 0.0,
            'max': max(fast_path_times) if fast_path_times else 0.0,
        },
        'slow_path': {
            'p50': percentile(slow_path_times, 0.5),
            'p95': percentile(slow_path_times, 0.95),
            'p99': percentile(slow_path_times, 0.99),
            'min': min(slow_path_times) if slow_path_times else 0.0,
            'max': max(slow_path_times) if slow_path_times else 0.0,
        },
    }

