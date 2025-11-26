from rest_framework import serializers
from .models import (
    Procedure,
    Fine,
    Office,
    Advisory,
    LegalSection,
    LegalDocument,
    IngestionJob,
)

class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = "__all__"

class FineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fine
        fields = "__all__"

class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = "__all__"

class AdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Advisory
        fields = "__all__"


class LegalDocumentSerializer(serializers.ModelSerializer):
    uploaded_file_url = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = "__all__"

    def get_uploaded_file_url(self, obj):
        if not obj.uploaded_file:
            return None
        try:
            url = obj.uploaded_file.url
        except ValueError:
            url = obj.uploaded_file.name
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_image_count(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "images" in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache["images"])
        return obj.images.count()


class LegalSectionSerializer(serializers.ModelSerializer):
    document = LegalDocumentSerializer(read_only=True)
    document_id = serializers.IntegerField(source="document.id", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = LegalSection
        fields = "__all__"

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not obj.document:
            return None
        path = f"/api/legal-documents/{obj.document.id}/download/"
        if request:
            return request.build_absolute_uri(path)
        return path


class IngestionJobSerializer(serializers.ModelSerializer):
    document = LegalDocumentSerializer(read_only=True)

    class Meta:
        model = IngestionJob
        fields = "__all__"

