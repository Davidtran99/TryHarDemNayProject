## Truy vấn mẫu cho Dashboard

### 1. Tổng quan theo ngày
```sql
SELECT date,
       total_requests,
        ROUND(intent_accuracy::numeric, 3) AS intent_accuracy,
        ROUND(average_latency_ms::numeric, 2) AS avg_latency_ms,
        ROUND(error_rate::numeric, 3) AS error_rate
FROM hue_portal_core_mlmetrics
ORDER BY date DESC
LIMIT 30;
```

### 2. Top intent trong ngày gần nhất
```sql
SELECT (intent_breakdown->>key) AS intent,
       (intent_breakdown->>key)::int AS count
FROM hue_portal_core_mlmetrics,
     LATERAL json_object_keys(intent_breakdown) AS key
WHERE date = CURRENT_DATE
ORDER BY count DESC;
```

### 3. Phân tích latency từ `audit_log`
```sql
SELECT date_trunc('hour', created_at) AS hour,
       AVG(latency_ms) AS avg_latency_ms,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms
FROM hue_portal_core_auditlog
WHERE created_at >= NOW() - INTERVAL '3 days'
  AND latency_ms IS NOT NULL
GROUP BY hour
ORDER BY hour;
```

Sử dụng các truy vấn trên để tạo widget Metabase/Grafana hiển thị xu hướng accuracy, latency, intent phổ biến.
