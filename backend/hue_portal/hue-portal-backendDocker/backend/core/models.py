from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
import uuid


def legal_document_upload_path(instance, filename):
    base = "legal_uploads"
    code = (instance.code or uuid.uuid4().hex).replace("/", "_")
    return f"{base}/{code}/{filename}"


def legal_document_image_upload_path(instance, filename):
    base = "legal_images"
    code = (instance.document.code if instance.document else uuid.uuid4().hex).replace("/", "_")
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"{base}/{code}/{timestamp}_{filename}"

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


class LegalDocument(models.Model):
    """Metadata + raw text for authoritative legal documents."""

    DOCUMENT_TYPES = [
        ("decision", "Decision"),
        ("circular", "Circular"),
        ("guideline", "Guideline"),
        ("plan", "Plan"),
        ("other", "Other"),
    ]

    code = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=500)
    doc_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, default="other")
    summary = models.TextField(blank=True)
    issued_by = models.CharField(max_length=200, blank=True)
    issued_at = models.DateField(null=True, blank=True)
    source_file = models.CharField(max_length=500, blank=True)
    uploaded_file = models.FileField(upload_to=legal_document_upload_path, null=True, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    file_checksum = models.CharField(max_length=128, blank=True)
    content_checksum = models.CharField(max_length=128, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    raw_text = models.TextField()
    raw_text_ocr = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tsv_body = SearchVectorField(null=True, editable=False)

    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="legal_document_tsv_idx"),
            models.Index(fields=["doc_type"]),
            models.Index(fields=["issued_at"]),
        ]
        ordering = ["title"]

    def search_vector(self) -> str:
        """Return concatenated searchable text."""
        fields = [
            self.title,
            self.code,
            self.summary,
            self.issued_by,
            self.raw_text,
        ]
        return " ".join(str(f) for f in fields if f)


class LegalSection(models.Model):
    """Structured snippet (chapter/section/article) for each legal document."""

    LEVEL_CHOICES = [
        ("chapter", "Chapter"),
        ("section", "Section"),
        ("article", "Article"),
        ("clause", "Clause"),
        ("note", "Note"),
        ("other", "Other"),
    ]

    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    section_code = models.CharField(max_length=120)
    section_title = models.CharField(max_length=500, blank=True)
    level = models.CharField(max_length=30, choices=LEVEL_CHOICES, default="other")
    order = models.PositiveIntegerField(default=0, db_index=True)
    page_start = models.IntegerField(null=True, blank=True)
    page_end = models.IntegerField(null=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_ocr = models.BooleanField(default=False)
    tsv_body = SearchVectorField(null=True, editable=False)
    embedding = models.BinaryField(null=True, blank=True, editable=False)

    class Meta:
        indexes = [
            GinIndex(fields=["tsv_body"], name="legal_section_tsv_idx"),
            models.Index(fields=["document", "order"]),
            models.Index(fields=["level"]),
        ]
        ordering = ["document", "order"]
        unique_together = ("document", "section_code", "order")

    def search_vector(self) -> str:
        fields = [
            self.section_title,
            self.section_code,
            self.content,
            self.excerpt,
        ]
        return " ".join(str(f) for f in fields if f)


class Synonym(models.Model):
    keyword = models.CharField(max_length=120, unique=True)
    alias = models.CharField(max_length=120)


class LegalDocumentImage(models.Model):
    """Metadata for images extracted from uploaded legal documents."""

    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=legal_document_image_upload_path)
    page_number = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["document", "page_number"]),
            models.Index(fields=["checksum"]),
        ]

    def __str__(self) -> str:
        return f"Image {self.id} of {self.document.code}"


class IngestionJob(models.Model):
    """Background ingestion task information."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=128)
    filename = models.CharField(max_length=255)
    document = models.ForeignKey(
        LegalDocument,
        related_name="ingestion_jobs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    storage_path = models.CharField(max_length=512, blank=True)
    progress = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"IngestionJob({self.code}, {self.status})"

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

