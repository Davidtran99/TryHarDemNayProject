"""
Migration to add embedding fields to models.
Uses pgvector extension for vector storage.
"""
from django.db import migrations, models
from django.contrib.postgres.operations import CreateExtension


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_mlmetrics"),
    ]

    operations = [
        # Note: pgvector extension not needed - using BinaryField instead
        # If you want to use pgvector later, install it in PostgreSQL first:
        # docker exec -it tryhardemnayproject-db-1 apt-get update && apt-get install -y postgresql-15-pgvector
        # Then enable: CREATE EXTENSION IF NOT EXISTS vector;
        
        # Add embedding field to Procedure
        migrations.AddField(
            model_name="procedure",
            name="embedding",
            field=models.BinaryField(null=True, blank=True, editable=False),
        ),
        # Add embedding field to Fine
        migrations.AddField(
            model_name="fine",
            name="embedding",
            field=models.BinaryField(null=True, blank=True, editable=False),
        ),
        # Add embedding field to Office
        migrations.AddField(
            model_name="office",
            name="embedding",
            field=models.BinaryField(null=True, blank=True, editable=False),
        ),
        # Add embedding field to Advisory
        migrations.AddField(
            model_name="advisory",
            name="embedding",
            field=models.BinaryField(null=True, blank=True, editable=False),
        ),
    ]

