"""
Admin API views for user management, activity monitoring, alerts, and import history.
All endpoints require admin role.
"""
import hashlib
from datetime import timedelta, datetime, time, date
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser

from .models import UserProfile, AuditLog, IngestionJob, SystemAlert, LegalDocument, LegalSection, LegalDocumentImage
from .serializers import AdminUserSerializer, IngestionJobSerializer, LegalDocumentSerializer
from .auth_views import _user_role

User = get_user_model()


class IsAdminPermission(permissions.BasePermission):
    """Permission class to check if user is admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _user_role(request.user) == UserProfile.Roles.ADMIN


class AdminUserListView(APIView):
    """List all users with pagination, role filter, and server-side search. Admin only."""
    permission_classes = [IsAdminPermission]

    def _get_cache_version(self):
        """Get current cache version for user list."""
        version = cache.get("admin_users_cache_version", 1)
        return version

    def _invalidate_cache(self):
        """Invalidate user list cache by incrementing version."""
        current_version = cache.get("admin_users_cache_version", 1)
        cache.set("admin_users_cache_version", current_version + 1, timeout=None)

    def get(self, request):
        role_filter = request.query_params.get("role")
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        # Build cache key with version
        cache_version = self._get_cache_version()
        cache_key_parts = [
            "admin_users",
            f"v{cache_version}",
            role_filter or "all",
            str(page),
            str(page_size),
            hashlib.md5(search.encode()).hexdigest()[:8] if search else "no_search",
        ]
        cache_key = "_".join(cache_key_parts)

        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)

        # Build queryset with optimized select_related and only()
        queryset = User.objects.select_related("profile").only(
            "id", "username", "email", "first_name", "last_name", "is_active", "date_joined"
        ).order_by("-date_joined")

        # Apply role filter
        if role_filter:
            queryset = queryset.filter(profile__role=role_filter)

        # Apply search filter (username or email)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        # Manual pagination
        start = (page - 1) * page_size
        end = start + page_size
        users = queryset[start:end]

        # Calculate total count (needed for pagination)
        # We always need the count for pagination to work properly
        total = queryset.count()

        serializer = AdminUserSerializer(users, many=True)

        response_data = {
            "results": serializer.data,
            "count": total,
            "page": page,
            "page_size": page_size,
        }

        # Cache the result for 30 seconds
        cache.set(cache_key, response_data, 30)

        return Response(response_data)


class AdminUserCreateView(APIView):
    """Create a new user. Admin only."""
    permission_classes = [IsAdminPermission]

    def post(self, request):
        from .serializers import RegisterSerializer

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Invalidate cache for user list
        AdminUserListView()._invalidate_cache()
        
        return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserUpdateView(APIView):
    """Update user role or is_active status. Admin only."""
    permission_classes = [IsAdminPermission]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Người dùng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        # Prevent admin from modifying themselves
        if user.id == request.user.id:
            return Response({"detail": "Bạn không thể thay đổi quyền của chính mình."}, status=status.HTTP_400_BAD_REQUEST)

        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Update role if provided
        if "role" in request.data:
            new_role = request.data["role"]
            if new_role not in [UserProfile.Roles.ADMIN, UserProfile.Roles.USER]:
                return Response({"detail": "Role không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
            profile.role = new_role
            profile.save()

        # Update is_active if provided
        if "is_active" in request.data:
            user.is_active = request.data["is_active"]
            user.save()

        # Invalidate cache for user list
        AdminUserListView()._invalidate_cache()
        
        return Response(AdminUserSerializer(user).data)


class AdminUserResetPasswordView(APIView):
    """Reset user password to a temporary password. Admin only."""
    permission_classes = [IsAdminPermission]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Người dùng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        import secrets
        import string

        # Generate temporary password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
        user.set_password(temp_password)
        user.save()

        return Response({
            "message": "Mật khẩu đã được reset.",
            "temporary_password": temp_password,  # In production, send via email instead
        })


def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string to extract device type and browser."""
    if not user_agent:
        return {"device_type": "unknown", "browser": "unknown"}

    ua_lower = user_agent.lower()

    # Detect device type
    device_type = "desktop"
    if "mobile" in ua_lower or "android" in ua_lower:
        device_type = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "tablet"

    # Detect browser
    browser = "unknown"
    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "edg" in ua_lower:
        browser = "Edge"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser = "Opera"

    return {"device_type": device_type, "browser": browser}


class AdminActivityLogsView(APIView):
    """List activity logs with IP, device, browser info, pagination, search, and filters. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        # Pagination params
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        
        # Search param (search by IP or location)
        search = request.query_params.get("search", "").strip()
        
        # Filter params
        device_type_filter = request.query_params.get("device_type")
        status_filter = request.query_params.get("status")
        
        # Timeframe (optional, defaults to all time if not specified)
        timeframe = request.query_params.get("timeframe")
        if timeframe:
            if timeframe == "24h":
                threshold = timezone.now() - timedelta(hours=24)
            elif timeframe == "7d":
                threshold = timezone.now() - timedelta(days=7)
            elif timeframe == "30d":
                threshold = timezone.now() - timedelta(days=30)
            else:
                threshold = None
        else:
            threshold = None

        # Build queryset
        queryset = AuditLog.objects.all().order_by("-created_at")
        
        if threshold:
            queryset = queryset.filter(created_at__gte=threshold)
        
        if search:
            # Search by IP address
            queryset = queryset.filter(ip__icontains=search)
        
        if device_type_filter:
            # We'll filter after parsing user_agent (see below)
            pass
        
        if status_filter:
            try:
                status_int = int(status_filter)
                queryset = queryset.filter(status=status_int)
            except ValueError:
                pass

        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        logs = queryset[start:end]

        results = []
        for log in logs:
            parsed = parse_user_agent(log.user_agent)
            device_type = parsed["device_type"]
            
            # Apply device_type filter if specified (after parsing)
            if device_type_filter:
                if device_type_filter.lower() == "desktop" and device_type != "desktop":
                    continue
                elif device_type_filter.lower() in ["mobile", "tablet"] and device_type not in ["mobile", "tablet"]:
                    continue
            
            # Get location from IP
            location = get_ip_location(log.ip)
            
            # Format device type for display
            display_device_type = "Desktop"
            if device_type == "mobile":
                display_device_type = "Mobile"
            elif device_type == "tablet":
                display_device_type = "Tablet"
            
            results.append({
                "id": log.id,
                "ip": str(log.ip) if log.ip else None,
                "device_type": display_device_type,
                "browser": parsed["browser"],
                "location": location or "Unknown",
                "timestamp": log.created_at.isoformat(),
                "status": log.status,
                "path": log.path,
                "query": log.query or "",
            })

        return Response({
            "results": results,
            "count": total_count,
            "page": page,
            "page_size": page_size,
        })


class AdminImportHistoryView(APIView):
    """List recent ingestion jobs. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        status_filter = request.query_params.get("status")
        limit = int(request.query_params.get("limit", 20))

        queryset = IngestionJob.objects.select_related("document").all().order_by("-created_at")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        jobs = queryset[:limit]
        serializer = IngestionJobSerializer(jobs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class AdminAlertsView(APIView):
    """List system alerts (unresolved by default). Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        alert_type = request.query_params.get("type")
        limit = int(request.query_params.get("limit", 50))
        unresolved_only = request.query_params.get("unresolved", "true").lower() == "true"

        queryset = SystemAlert.objects.all().order_by("-created_at")

        if unresolved_only:
            queryset = queryset.filter(resolved_at__isnull=True)

        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        alerts = queryset[:limit]

        results = []
        for alert in alerts:
            results.append({
                "id": alert.id,
                "alert_type": alert.alert_type,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "created_at": alert.created_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata,
            })

        return Response({"results": results, "count": len(results)})


def format_time_ago(timestamp):
    """Format timestamp to human-readable time ago string."""
    now = timezone.now()
    if timestamp.tzinfo is None:
        timestamp = timezone.make_aware(timestamp)
    
    diff = now - timestamp
    
    if diff.days > 0:
        if diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


class AdminDashboardStatsView(APIView):
    """Get dashboard statistics (total documents, active users, pending approvals, system alerts). Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        # Get current counts
        total_documents = LegalDocument.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        pending_approvals = IngestionJob.objects.filter(status=IngestionJob.STATUS_PENDING).count()
        system_alerts = SystemAlert.objects.filter(resolved_at__isnull=True).count()

        # Calculate percentage changes (comparing last 7 days to previous 7 days)
        now = timezone.now()
        last_7_days_start = now - timedelta(days=7)
        previous_7_days_start = now - timedelta(days=14)
        
        # Documents change
        docs_last_7 = LegalDocument.objects.filter(created_at__gte=last_7_days_start).count()
        docs_prev_7 = LegalDocument.objects.filter(
            created_at__gte=previous_7_days_start,
            created_at__lt=last_7_days_start
        ).count()
        total_documents_change = 0.0
        if docs_prev_7 > 0:
            total_documents_change = ((docs_last_7 - docs_prev_7) / docs_prev_7) * 100
        elif docs_last_7 > 0:
            total_documents_change = 100.0

        # Active users change (users activated in last 7 days)
        users_last_7 = User.objects.filter(
            is_active=True,
            date_joined__gte=last_7_days_start
        ).count()
        users_prev_7 = User.objects.filter(
            is_active=True,
            date_joined__gte=previous_7_days_start,
            date_joined__lt=last_7_days_start
        ).count()
        active_users_change = 0.0
        if users_prev_7 > 0:
            active_users_change = ((users_last_7 - users_prev_7) / users_prev_7) * 100
        elif users_last_7 > 0:
            active_users_change = 100.0

        # Pending approvals change
        pending_last_7 = IngestionJob.objects.filter(
            status=IngestionJob.STATUS_PENDING,
            created_at__gte=last_7_days_start
        ).count()
        pending_prev_7 = IngestionJob.objects.filter(
            status=IngestionJob.STATUS_PENDING,
            created_at__gte=previous_7_days_start,
            created_at__lt=last_7_days_start
        ).count()
        pending_approvals_change = 0.0
        if pending_prev_7 > 0:
            pending_approvals_change = ((pending_last_7 - pending_prev_7) / pending_prev_7) * 100
        elif pending_last_7 > 0:
            pending_approvals_change = 100.0

        # System alerts change (negative means fewer alerts = good)
        alerts_last_7 = SystemAlert.objects.filter(
            resolved_at__isnull=True,
            created_at__gte=last_7_days_start
        ).count()
        alerts_prev_7 = SystemAlert.objects.filter(
            resolved_at__isnull=True,
            created_at__gte=previous_7_days_start,
            created_at__lt=last_7_days_start
        ).count()
        system_alerts_change = 0.0
        if alerts_prev_7 > 0:
            system_alerts_change = ((alerts_last_7 - alerts_prev_7) / alerts_prev_7) * 100
        elif alerts_last_7 > 0:
            system_alerts_change = 100.0
        else:
            # If no alerts in last period but had alerts before, it's a decrease
            if alerts_prev_7 > 0:
                system_alerts_change = -100.0

        return Response({
            "total_documents": total_documents,
            "total_documents_change": round(total_documents_change, 1),
            "active_users": active_users,
            "active_users_change": round(active_users_change, 1),
            "pending_approvals": pending_approvals,
            "pending_approvals_change": round(pending_approvals_change, 1),
            "system_alerts": system_alerts,
            "system_alerts_change": round(system_alerts_change, 1),
        })


class AdminDashboardDocumentsWeekView(APIView):
    """Get documents processed this week data for bar chart. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        # Use local date + timezone-aware boundaries so stats align with UI expectations
        today = timezone.localdate()
        last_7_days_start = timezone.make_aware(
            datetime.combine(today - timedelta(days=6), time.min),
            timezone.get_current_timezone(),
        )
        previous_7_days_start = last_7_days_start - timedelta(days=7)

        # Get completed ingestion jobs (documents actually processed) in last 7 days, grouped by finished_at day
        ingestion_last_7 = (
            IngestionJob.objects.filter(
                status=IngestionJob.STATUS_COMPLETED,
                finished_at__isnull=False,
                finished_at__gte=last_7_days_start,
            )
            .annotate(date=TruncDate("finished_at", tzinfo=timezone.get_current_timezone()))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Create a dict for easy lookup by exact date
        from datetime import date as date_type

        daily_counts_dict = {}
        for item in ingestion_last_7:
            day = item["date"]
            if isinstance(day, date_type):
                daily_counts_dict[day] = item["count"]

        # Get totals for the same completed-ingestion dataset
        total_last_7 = (
            IngestionJob.objects.filter(
                status=IngestionJob.STATUS_COMPLETED,
                finished_at__isnull=False,
                finished_at__gte=last_7_days_start,
            ).count()
        )
        total_prev_7 = (
            IngestionJob.objects.filter(
                status=IngestionJob.STATUS_COMPLETED,
                finished_at__isnull=False,
                finished_at__gte=previous_7_days_start,
                finished_at__lt=last_7_days_start,
            ).count()
        )

        # Calculate percentage change
        change_percent = 0.0
        if total_prev_7 > 0:
            change_percent = ((total_last_7 - total_prev_7) / total_prev_7) * 100
        elif total_last_7 > 0:
            change_percent = 100.0

        # Build daily data array for the last 7 days (from 6 days ago to today)
        daily_data = []
        for i in range(6, -1, -1):  # 6 days ago to today
            day_date = today - timedelta(days=i)
            day_name = day_date.strftime("%a")  # Mon, Tue, etc.
            count = daily_counts_dict.get(day_date, 0)
            daily_data.append({"day": day_name, "count": count})

        return Response({
            "total": total_last_7,
            "change_percent": round(change_percent, 1),
            "daily_data": daily_data,
        })


class AdminDashboardRecentActivityView(APIView):
    """Get recent activity list combining document uploads, user role changes, alerts, and approvals. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        activities = []

        # 1. Document uploads (from completed IngestionJobs)
        uploads = IngestionJob.objects.filter(
            status=IngestionJob.STATUS_COMPLETED
        ).select_related('document').order_by('-created_at')[:limit]
        
        for job in uploads:
            filename = job.filename or "Unknown file"
            # Try to get user from metadata or use system
            user_name = job.metadata.get('uploaded_by', 'System')
            activities.append({
                "type": "document_upload",
                "icon": "upload_file",
                "title": "New document uploaded",
                "description": f'"{filename}" by {user_name}',
                "time_ago": format_time_ago(job.created_at),
                "timestamp": job.created_at.isoformat(),
            })

        # 2. System alerts (unresolved)
        alerts = SystemAlert.objects.filter(
            resolved_at__isnull=True
        ).order_by('-created_at')[:limit]
        
        for alert in alerts:
            activities.append({
                "type": "system_alert",
                "icon": "warning",
                "title": "System Alert",
                "description": alert.message,
                "time_ago": format_time_ago(alert.created_at),
                "timestamp": alert.created_at.isoformat(),
                "severity": alert.severity,
            })

        # 3. Document approvals (completed jobs, can be same as uploads but we'll treat separately)
        approvals = IngestionJob.objects.filter(
            status=IngestionJob.STATUS_COMPLETED
        ).select_related('document').order_by('-finished_at')[:limit]
        
        for job in approvals:
            if job.finished_at:
                filename = job.filename or "Unknown file"
                activities.append({
                    "type": "document_approval",
                    "icon": "check_circle",
                    "title": "Document approved",
                    "description": f'"{filename}"',
                    "time_ago": format_time_ago(job.finished_at),
                    "timestamp": job.finished_at.isoformat(),
                })

        # 4. User role changes (from AuditLog - we'll look for role change patterns)
        # For now, we'll use a simple approach: check audit logs for user-related changes
        # In a real system, you might have a separate UserRoleChange model
        role_changes = AuditLog.objects.filter(
            path__contains='/admin/users/',
            status=200
        ).order_by('-created_at')[:5]
        
        for log in role_changes:
            # Extract username from path if possible
            path_parts = log.path.split('/')
            if len(path_parts) > 3:
                user_id = path_parts[-2] if path_parts[-2].isdigit() else None
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        activities.append({
                            "type": "user_role_change",
                            "icon": "person_add",
                            "title": "User role changed",
                            "description": f"{user.username} role updated",
                            "time_ago": format_time_ago(log.created_at),
                            "timestamp": log.created_at.isoformat(),
                        })
                    except User.DoesNotExist:
                        pass

        # 5. Recent login attempts (from AuditLog - successful logins)
        recent_logins = AuditLog.objects.filter(
            path__contains='/auth/login/',
            status=200
        ).order_by('-created_at')[:3]
        
        for log in recent_logins:
            activities.append({
                "type": "user_login",
                "icon": "login",
                "title": "User login",
                "description": f"Successful login from {log.ip or 'unknown IP'}",
                "time_ago": format_time_ago(log.created_at),
                "timestamp": log.created_at.isoformat(),
            })

        # 6. Recent document views/searches (from AuditLog - search and chat endpoints)
        recent_searches = AuditLog.objects.filter(
            Q(path__contains='/search/') | Q(path__contains='/chat/'),
            status=200
        ).order_by('-created_at')[:3]
        
        for log in recent_searches:
            activity_type = "document_search" if '/search/' in log.path else "chat_query"
            activities.append({
                "type": activity_type,
                "icon": "search" if '/search/' in log.path else "chat",
                "title": "Search query" if '/search/' in log.path else "Chat query",
                "description": f"Query from {log.ip or 'unknown IP'}",
                "time_ago": format_time_ago(log.created_at),
                "timestamp": log.created_at.isoformat(),
            })

        # Sort all activities by timestamp (most recent first) and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        activities = activities[:limit]

        return Response({"results": activities})


def get_ip_location(ip_address):
    """
    Get location from IP address using ip-api.com (free tier).
    Returns location string like "Hue, Vietnam" or None if unavailable.
    Caches results to avoid rate limits.
    """
    if not ip_address:
        return None
    
    # Skip local/private IPs
    ip_str = str(ip_address)
    if ip_str.startswith(('127.', '192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.')):
        return None
    
    # Check cache first
    cache_key = f"ip_location_{ip_str}"
    cached_location = cache.get(cache_key)
    if cached_location is not None:
        return cached_location
    
    try:
        import requests
        # Use ip-api.com free tier (45 requests/minute)
        response = requests.get(
            f"http://ip-api.com/json/{ip_str}",
            params={"fields": "status,message,city,country"},
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                country = data.get("country", "")
                if city and country:
                    location = f"{city}, {country}"
                    # Cache for 24 hours
                    cache.set(cache_key, location, 86400)
                    return location
    except Exception:
        # Silently fail - don't block the request
        pass
    
    return None


class AdminSystemLogsStatsView(APIView):
    """Get System Logs statistics for 3 cards. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h_start = now - timedelta(hours=24)
        previous_24h_start = last_24h_start - timedelta(hours=24)

        # Active Users: unique IPs in last 24h
        active_users_last_24h = AuditLog.objects.filter(
            created_at__gte=last_24h_start,
            ip__isnull=False
        ).values('ip').distinct().count()
        
        active_users_prev_24h = AuditLog.objects.filter(
            created_at__gte=previous_24h_start,
            created_at__lt=last_24h_start,
            ip__isnull=False
        ).values('ip').distinct().count()
        
        active_users_change = 0.0
        if active_users_prev_24h > 0:
            active_users_change = ((active_users_last_24h - active_users_prev_24h) / active_users_prev_24h) * 100
        elif active_users_last_24h > 0:
            active_users_change = 100.0

        # Total Devices 24h: unique device types in last 24h
        # We need to parse user_agent for each log to get device type
        logs_last_24h = AuditLog.objects.filter(created_at__gte=last_24h_start)
        device_types_set = set()
        for log in logs_last_24h[:1000]:  # Limit to avoid too many queries
            parsed = parse_user_agent(log.user_agent)
            device_type = parsed["device_type"]
            if device_type == "mobile" or device_type == "tablet":
                device_types_set.add("Mobile & Tablet")
            elif device_type == "desktop":
                device_types_set.add("Desktop")
            else:
                device_types_set.add("Unknown")
        
        total_devices_24h = len(device_types_set)
        
        # For previous period, do similar calculation
        logs_prev_24h = AuditLog.objects.filter(
            created_at__gte=previous_24h_start,
            created_at__lt=last_24h_start
        )
        device_types_prev_set = set()
        for log in logs_prev_24h[:1000]:
            parsed = parse_user_agent(log.user_agent)
            device_type = parsed["device_type"]
            if device_type == "mobile" or device_type == "tablet":
                device_types_prev_set.add("Mobile & Tablet")
            elif device_type == "desktop":
                device_types_prev_set.add("Desktop")
            else:
                device_types_prev_set.add("Unknown")
        
        total_devices_prev_24h = len(device_types_prev_set)
        
        total_devices_change = 0.0
        if total_devices_prev_24h > 0:
            total_devices_change = ((total_devices_24h - total_devices_prev_24h) / total_devices_prev_24h) * 100
        elif total_devices_24h > 0:
            total_devices_change = 100.0

        # Accesses Today: total requests today
        accesses_today = AuditLog.objects.filter(created_at__gte=today_start).count()
        yesterday_start = today_start - timedelta(days=1)
        accesses_yesterday = AuditLog.objects.filter(
            created_at__gte=yesterday_start,
            created_at__lt=today_start
        ).count()
        
        accesses_today_change = 0.0
        if accesses_yesterday > 0:
            accesses_today_change = ((accesses_today - accesses_yesterday) / accesses_yesterday) * 100
        elif accesses_today > 0:
            accesses_today_change = 100.0

        return Response({
            "active_users": active_users_last_24h,
            "active_users_change": round(active_users_change, 1),
            "total_devices_24h": total_devices_24h,
            "total_devices_change": round(total_devices_change, 1),
            "accesses_today": accesses_today,
            "accesses_today_change": round(accesses_today_change, 1),
        })


class AdminSystemLogsDeviceStatsView(APIView):
    """Get device type statistics for donut chart. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        now = timezone.now()
        last_24h_start = now - timedelta(hours=24)
        
        logs = AuditLog.objects.filter(created_at__gte=last_24h_start)
        
        desktop_count = 0
        mobile_tablet_count = 0
        
        for log in logs:
            parsed = parse_user_agent(log.user_agent)
            device_type = parsed["device_type"]
            if device_type == "mobile" or device_type == "tablet":
                mobile_tablet_count += 1
            elif device_type == "desktop":
                desktop_count += 1
        
        total = desktop_count + mobile_tablet_count
        
        device_types = []
        if desktop_count > 0:
            device_types.append({
                "type": "Desktop",
                "count": desktop_count,
                "percentage": round((desktop_count / total * 100) if total > 0 else 0, 1)
            })
        if mobile_tablet_count > 0:
            device_types.append({
                "type": "Mobile & Tablet",
                "count": mobile_tablet_count,
                "percentage": round((mobile_tablet_count / total * 100) if total > 0 else 0, 1)
            })
        
        return Response({
            "total": total,
            "device_types": device_types,
        })


class AdminSystemLogsUsageOverTimeView(APIView):
    """Get usage over time data for bar chart (7 days). Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()
        
        # Calculate start of last 7 days (inclusive of today)
        last_7_days_start = timezone.make_aware(datetime.combine(today - timedelta(days=6), time.min))
        
        # Get logs created in last 7 days, grouped by day
        logs_last_7 = AuditLog.objects.filter(
            created_at__gte=last_7_days_start
        ).annotate(
            date=TruncDate('created_at', tzinfo=timezone.get_current_timezone())
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        daily_counts_dict = {item['date']: item['count'] for item in logs_last_7}

        # Build daily data array for the last 7 days (from 6 days ago to today)
        daily_data = []
        for i in range(6, -1, -1):  # 6 days ago to today
            day_date = today - timedelta(days=i)
            day_name = day_date.strftime('%a')  # Get actual day name (Mon, Tue, etc.)
            count = daily_counts_dict.get(day_date, 0)
            daily_data.append({"day": day_name, "count": count})

        return Response({
            "daily_data": daily_data,
        })


def get_document_status(doc: LegalDocument) -> str:
    """Determine document status based on latest IngestionJob."""
    latest_job = doc.ingestion_jobs.order_by('-created_at').first()
    if latest_job and latest_job.status == IngestionJob.STATUS_COMPLETED:
        return "active"
    return "archived"


def get_document_category(doc: LegalDocument) -> str:
    """Map doc_type to display category name."""
    category_map = {
        "decision": "Decision",
        "circular": "Circular",
        "guideline": "Guideline",
        "plan": "Plan",
        "other": "Other",
    }
    return category_map.get(doc.doc_type, doc.doc_type.title())


def get_file_type_display(mime_type: str) -> str:
    """Map mime_type to display name."""
    if "pdf" in mime_type.lower():
        return "PDF"
    elif "wordprocessingml" in mime_type.lower() or "msword" in mime_type.lower():
        return "DOCX"
    elif "spreadsheetml" in mime_type.lower():
        return "XLSX"
    elif "presentationml" in mime_type.lower():
        return "PPTX"
    else:
        return "Other"


class AdminDocumentListView(APIView):
    """List documents with pagination, search, and filters. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request):
        # Pagination params
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        
        # Search param
        search = request.query_params.get("search", "").strip()
        
        # Filter params
        category_filter = request.query_params.get("category")  # doc_type
        status_filter = request.query_params.get("status")  # active/archived
        file_type_filter = request.query_params.get("file_type")  # PDF, DOCX, etc.
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        # Build queryset - ALWAYS query directly from database, NO CACHE
        # This ensures frontend always gets the latest data from database
        queryset = LegalDocument.objects.all().order_by("-created_at")
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(code__icontains=search) |
                Q(summary__icontains=search)
            )
        
        # Apply category filter (doc_type)
        if category_filter:
            queryset = queryset.filter(doc_type=category_filter)
        
        # Apply file type filter (mime_type)
        if file_type_filter:
            if file_type_filter.lower() == "pdf":
                queryset = queryset.filter(mime_type__icontains="pdf")
            elif file_type_filter.lower() == "docx":
                queryset = queryset.filter(
                    Q(mime_type__icontains="wordprocessingml") |
                    Q(mime_type__icontains="msword")
                )
            elif file_type_filter.lower() == "other":
                queryset = queryset.exclude(
                    Q(mime_type__icontains="pdf") |
                    Q(mime_type__icontains="wordprocessingml") |
                    Q(mime_type__icontains="msword")
                )
        
        # Apply date range filter
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(created_at__date__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(created_at__date__lte=to_date)
            except ValueError:
                pass

        # Apply status filter (based on IngestionJob)
        if status_filter:
            if status_filter == "active":
                # Documents with at least one completed ingestion job
                queryset = queryset.filter(
                    ingestion_jobs__status=IngestionJob.STATUS_COMPLETED
                ).distinct()
            elif status_filter == "archived":
                # Documents without completed ingestion jobs
                completed_doc_ids = LegalDocument.objects.filter(
                    ingestion_jobs__status=IngestionJob.STATUS_COMPLETED
                ).values_list('id', flat=True).distinct()
                queryset = queryset.exclude(id__in=completed_doc_ids)

        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        documents = queryset[start:end]

        results = []
        for doc in documents:
            # Determine status
            status = get_document_status(doc)
            
            # Get file type display
            file_type_display = get_file_type_display(doc.mime_type or "")
            
            results.append({
                "id": doc.id,
                "code": doc.code,
                "title": doc.title,
                "doc_type": doc.doc_type,
                "category": get_document_category(doc),
                "date_uploaded": doc.created_at.isoformat(),
                "status": status,
                "file_type": doc.mime_type or "",
                "file_type_display": file_type_display,
                "file_size": doc.file_size,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            })

        return Response({
            "results": results,
            "count": total_count,
            "page": page,
            "page_size": page_size,
        })


class AdminDocumentDetailView(APIView):
    """Get, update, or delete document. Admin only."""
    permission_classes = [IsAdminPermission]

    def get(self, request, doc_id):
        try:
            doc = LegalDocument.objects.get(id=doc_id)
        except LegalDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LegalDocumentSerializer(doc, context={"request": request})
        data = serializer.data
        
        # Add computed fields
        data["status"] = get_document_status(doc)
        data["category"] = get_document_category(doc)
        data["file_type_display"] = get_file_type_display(doc.mime_type or "")
        
        return Response(data)

    def patch(self, request, doc_id):
        try:
            doc = LegalDocument.objects.get(id=doc_id)
        except LegalDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Update allowed fields
        allowed_fields = ["title", "code", "doc_type", "summary", "issued_by", "issued_at", "source_url"]
        for field in allowed_fields:
            if field in request.data:
                setattr(doc, field, request.data[field])
        
        doc.save()
        
        serializer = LegalDocumentSerializer(doc, context={"request": request})
        data = serializer.data
        data["status"] = get_document_status(doc)
        data["category"] = get_document_category(doc)
        data["file_type_display"] = get_file_type_display(doc.mime_type or "")
        
        return Response(data)

    def delete(self, request, doc_id):
        try:
            doc = LegalDocument.objects.get(id=doc_id)
        except LegalDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete related objects
        LegalSection.objects.filter(document=doc).delete()
        LegalDocumentImage.objects.filter(document=doc).delete()
        IngestionJob.objects.filter(document=doc).delete()
        
        # Delete the document
        doc.delete()
        
        return Response({"message": "Document deleted successfully."}, status=status.HTTP_200_OK)


class AdminDocumentImportView(APIView):
    """Import document. Admin only. Reuses legal_document_upload logic."""
    permission_classes = [IsAdminPermission]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from .services import enqueue_ingestion_job
        
        upload = request.FILES.get("file")
        if not upload:
            return Response({"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        code = (request.data.get("code") or "").strip()
        if not code:
            return Response({"error": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

        metadata = {
            "code": code,
            "title": request.data.get("title") or code,
            "doc_type": request.data.get("doc_type", "other"),
            "summary": request.data.get("summary", ""),
            "issued_by": request.data.get("issued_by", ""),
            "issued_at": request.data.get("issued_at"),
            "source_url": request.data.get("source_url", ""),
            "mime_type": request.data.get("mime_type") or getattr(upload, "content_type", ""),
            "metadata": {},
        }
        extra_meta = request.data.get("metadata")
        if extra_meta:
            import json
            try:
                metadata["metadata"] = json.loads(extra_meta) if isinstance(extra_meta, str) else extra_meta
            except Exception:
                return Response({"error": "metadata must be valid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = enqueue_ingestion_job(
                file_obj=upload,
                filename=upload.name,
                metadata=metadata,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serialized = IngestionJobSerializer(job, context={"request": request}).data
        return Response(serialized, status=status.HTTP_202_ACCEPTED)

