from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.search
import django.contrib.postgres.indexes


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_conversation_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocument",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=120, unique=True)),
                ("title", models.CharField(max_length=500)),
                ("doc_type", models.CharField(blank=True, max_length=50)),
                ("issued_date", models.DateField(blank=True, null=True)),
                ("signer", models.CharField(blank=True, max_length=200)),
                ("agency", models.CharField(blank=True, max_length=200)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("raw_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.CreateModel(
            name="LegalSection",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.IntegerField()),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("article", "Điều"),
                            ("clause", "Khoản"),
                            ("point", "Điểm"),
                            ("other", "Khác"),
                        ],
                        default="article",
                        max_length=20,
                    ),
                ),
                ("section_code", models.CharField(blank=True, max_length=120)),
                ("section_title", models.CharField(blank=True, max_length=500)),
                ("content", models.TextField()),
                ("page_start", models.IntegerField(blank=True, null=True)),
                ("page_end", models.IntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("tsv_body", django.contrib.postgres.search.SearchVectorField(editable=False, null=True)),
                ("embedding", models.BinaryField(blank=True, editable=False, null=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="core.legaldocument",
                    ),
                ),
            ],
            options={
                "ordering": ["document", "order"],
            },
        ),
        migrations.AddIndex(
            model_name="legalsection",
            index=django.contrib.postgres.indexes.GinIndex(fields=["tsv_body"], name="legalsection_tsv_idx"),
        ),
        migrations.AddIndex(
            model_name="legalsection",
            index=models.Index(fields=["document", "order"], name="core_legalse_document_6a7707_idx"),
        ),
    ]

