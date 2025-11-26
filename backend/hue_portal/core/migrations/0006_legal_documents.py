from django.db import migrations, models
import django.contrib.postgres.search
import django.contrib.postgres.indexes
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_conversation_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocument",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=100, unique=True)),
                ("title", models.CharField(max_length=500)),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("decision", "Decision"),
                            ("circular", "Circular"),
                            ("guideline", "Guideline"),
                            ("plan", "Plan"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=30,
                    ),
                ),
                ("summary", models.TextField(blank=True)),
                ("issued_by", models.CharField(blank=True, max_length=200)),
                ("issued_at", models.DateField(blank=True, null=True)),
                ("source_file", models.CharField(max_length=500)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("page_count", models.IntegerField(blank=True, null=True)),
                ("raw_text", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tsv_body",
                    django.contrib.postgres.search.SearchVectorField(
                        editable=False, null=True
                    ),
                ),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.CreateModel(
            name="LegalSection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("section_code", models.CharField(max_length=120)),
                ("section_title", models.CharField(blank=True, max_length=500)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("chapter", "Chapter"),
                            ("section", "Section"),
                            ("article", "Article"),
                            ("clause", "Clause"),
                            ("note", "Note"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=30,
                    ),
                ),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("page_start", models.IntegerField(blank=True, null=True)),
                ("page_end", models.IntegerField(blank=True, null=True)),
                ("content", models.TextField()),
                ("excerpt", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "tsv_body",
                    django.contrib.postgres.search.SearchVectorField(
                        editable=False, null=True
                    ),
                ),
                (
                    "embedding",
                    models.BinaryField(blank=True, editable=False, null=True),
                ),
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
                "unique_together": {("document", "section_code", "order")},
            },
        ),
        migrations.AddIndex(
            model_name="legaldocument",
            index=models.Index(fields=["doc_type"], name="core_legaldo_doc_typ_01ee44_idx"),
        ),
        migrations.AddIndex(
            model_name="legaldocument",
            index=models.Index(fields=["issued_at"], name="core_legaldo_issued__df806a_idx"),
        ),
        migrations.AddIndex(
            model_name="legaldocument",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["tsv_body"], name="legal_document_tsv_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="legalsection",
            index=models.Index(fields=["document", "order"], name="core_legalse_documen_1cb98e_idx"),
        ),
        migrations.AddIndex(
            model_name="legalsection",
            index=models.Index(fields=["level"], name="core_legalse_level_e3a6a8_idx"),
        ),
        migrations.AddIndex(
            model_name="legalsection",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["tsv_body"], name="legal_section_tsv_idx"
            ),
        ),
    ]

