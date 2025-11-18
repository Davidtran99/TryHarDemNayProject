from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
import uuid

class Procedure(models.Model):
    title = models.CharField(max_length=500)
    domain = models.CharField(max_length=100, db_index=True)  # ANTT/Cư trú/PCCC/GT
    level = models.CharField(max_length=50, blank=True)  # Tỉnh/Huyện/Xã
    conditions = models.TextField(blank=True)
    dossier = models.TextField(blank=True)
    fee = models.CharField(max_length=200, blank=True)
    duration = models.CharField(max_length=200, blank=True)
    authority = models.CharField(max_length=300, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    tsv_body = SearchVectorField(null=True, editable=False)
    embedding = models.BinaryField(null=True, blank=True, editable=False)
    
    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="procedure_tsv_idx"),
        ]
    
    def search_vector(self) -> str:
        """Create searchable text vector for this procedure."""
        fields = [self.title, self.domain, self.level, self.conditions, self.dossier]
        return " ".join(str(f) for f in fields if f)

class Fine(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=500)
    article = models.CharField(max_length=100, blank=True)
    decree = models.CharField(max_length=100, blank=True)
    min_fine = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    max_fine = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    license_points = models.CharField(max_length=50, blank=True)
    remedial = models.TextField(blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    tsv_body = SearchVectorField(null=True, editable=False)
    embedding = models.BinaryField(null=True, blank=True, editable=False)
    
    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="fine_tsv_idx"),
        ]
    
    def search_vector(self) -> str:
        """Create searchable text vector for this fine."""
        fields = [self.name, self.code, self.article, self.decree, self.remedial]
        return " ".join(str(f) for f in fields if f)

class Office(models.Model):
    unit_name = models.CharField(max_length=300)
    address = models.CharField(max_length=500, blank=True)
    district = models.CharField(max_length=100, blank=True, db_index=True)
    working_hours = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    service_scope = models.CharField(max_length=300, blank=True)
    tsv_body = SearchVectorField(null=True, editable=False)
    embedding = models.BinaryField(null=True, blank=True, editable=False)
    
    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="office_tsv_idx"),
        ]
    
    def search_vector(self) -> str:
        """Create searchable text vector for this office."""
        fields = [self.unit_name, self.address, self.district, self.service_scope]
        return " ".join(str(f) for f in fields if f)

class Advisory(models.Model):
    title = models.CharField(max_length=500)
    summary = models.TextField()
    source_url = models.URLField(max_length=1000, blank=True)
    published_at = models.DateField(null=True, blank=True)
    tsv_body = SearchVectorField(null=True, editable=False)
    embedding = models.BinaryField(null=True, blank=True, editable=False)
    
    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="advisory_tsv_idx"),
        ]
    
    def search_vector(self) -> str:
        """Create searchable text vector for this advisory."""
        fields = [self.title, self.summary]
        return " ".join(str(f) for f in fields if f)

class Synonym(models.Model):
    keyword = models.CharField(max_length=120, unique=True)
    alias = models.CharField(max_length=120)

class AuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    path = models.CharField(max_length=300)
    query = models.CharField(max_length=500, blank=True)
    status = models.IntegerField(default=200)
    intent = models.CharField(max_length=50, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    latency_ms = models.FloatField(null=True, blank=True)


class MLMetrics(models.Model):
    date = models.DateField(unique=True)
    total_requests = models.IntegerField(default=0)
    intent_accuracy = models.FloatField(null=True, blank=True)
    average_latency_ms = models.FloatField(null=True, blank=True)
    error_rate = models.FloatField(null=True, blank=True)
    intent_breakdown = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-date"]
        verbose_name = "ML Metrics"
        verbose_name_plural = "ML Metrics"


class ConversationSession(models.Model):
    """Model to store conversation sessions for context management."""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Conversation Session"
        verbose_name_plural = "Conversation Sessions"
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["user_id", "-updated_at"]),
        ]
    
    def __str__(self):
        return f"Session {self.session_id}"


class ConversationMessage(models.Model):
    """Model to store individual messages in a conversation session."""
    ROLE_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]
    
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True, null=True)
    entities = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Conversation Message"
        verbose_name_plural = "Conversation Messages"
        indexes = [
            models.Index(fields=["session", "timestamp"]),
            models.Index(fields=["session", "role", "timestamp"]),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

