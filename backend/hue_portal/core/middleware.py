import time
from typing import Any

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from .models import AuditLog

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request: HttpRequest, response: HttpResponse):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        # CSP tối giản; mở rộng khi cần
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:;")
        return response

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        request._audit_start = time.perf_counter()

    def process_response(self, request: HttpRequest, response: HttpResponse):
        try:
            path = request.path[:300]
            query = request.META.get("QUERY_STRING", "")[:500]
            ua = request.META.get("HTTP_USER_AGENT", "")[:300]
            ip = request.META.get("REMOTE_ADDR")
            latency_ms = None
            start = getattr(request, "_audit_start", None)
            if start is not None:
                latency_ms = (time.perf_counter() - start) * 1000

            intent = ""
            confidence = None
            data: Any = getattr(response, "data", None)
            if isinstance(data, dict):
                intent = str(data.get("intent") or "")[:50]
                confidence_value = data.get("confidence")
                try:
                    confidence = float(confidence_value) if confidence_value is not None else None
                except (TypeError, ValueError):
                    confidence = None

            AuditLog.objects.create(
                path=path,
                query=query,
                user_agent=ua,
                ip=ip,
                status=response.status_code,
                intent=intent,
                confidence=confidence,
                latency_ms=latency_ms,
            )
        except Exception:
            # Không làm hỏng request nếu ghi log lỗi
            pass
        return response

