from django.db import migrations, models
import hue_portal.core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_legal_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="legaldocument",
            name="file_checksum",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="legaldocument",
            name="file_size",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="legaldocument",
            name="mime_type",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="legaldocument",
            name="original_filename",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="legaldocument",
            name="uploaded_file",
            field=models.FileField(blank=True, null=True, upload_to=hue_portal.core.models.legal_document_upload_path),
        ),
        migrations.AlterField(
            model_name="legaldocument",
            name="source_file",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.CreateModel(
            name="LegalDocumentImage",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=hue_portal.core.models.legal_document_image_upload_path)),
                ("page_number", models.IntegerField(blank=True, null=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("width", models.IntegerField(blank=True, null=True)),
                ("height", models.IntegerField(blank=True, null=True)),
                ("checksum", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="images",
                        to="core.legaldocument",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="legaldocumentimage",
            index=models.Index(fields=["document", "page_number"], name="core_legald_documen_b2f145_idx"),
        ),
        migrations.AddIndex(
            model_name="legaldocumentimage",
            index=models.Index(fields=["checksum"], name="core_legald_checksum_90ccce_idx"),
        ),
    ]

