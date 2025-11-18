from rest_framework import serializers
from .models import Procedure, Fine, Office, Advisory

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

