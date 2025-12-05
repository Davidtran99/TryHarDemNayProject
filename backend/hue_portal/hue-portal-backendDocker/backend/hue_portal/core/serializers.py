from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    Procedure,
    Fine,
    Office,
    Advisory,
    LegalSection,
    LegalDocument,
    IngestionJob,
    UserProfile,
)

User = get_user_model()

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


class AuthUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management with role and status."""
    role = serializers.CharField(source="profile.role", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role = serializers.ChoiceField(choices=UserProfile.Roles.choices, default=UserProfile.Roles.USER)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Tên đăng nhập đã tồn tại.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email đã tồn tại.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        role = validated_data.pop("role", UserProfile.Roles.USER)
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        return user
