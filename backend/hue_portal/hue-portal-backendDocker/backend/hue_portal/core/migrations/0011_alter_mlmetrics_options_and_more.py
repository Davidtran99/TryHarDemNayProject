"""
Simplified migration 0011 to avoid permission issues on Hugging Face Space.

Original migration was renaming PostgreSQL indexes and altering ID fields,
which requires table/index ownership. On Space we only need the updated
options for MlMetrics (ordering / verbose names) – the schema is already
compatible with the code.

So this migration is intentionally "no-op" for schema-changing operations,
and only keeps the AlterModelOptions. This allows migrations to complete
without requiring owner privileges.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_legaldocument_content_checksum"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="mlmetrics",
            options={
                "ordering": ["-date"],
                "verbose_name": "ML Metrics",
                "verbose_name_plural": "ML Metrics",
            },
        ),
        # All index renames and AlterField operations are intentionally removed
        # to avoid permission errors on managed PostgreSQL instances.
    ]
