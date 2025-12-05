from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_enable_bm25"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="intent",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="confidence",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="latency_ms",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
