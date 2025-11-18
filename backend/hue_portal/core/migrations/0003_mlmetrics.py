from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_auditlog_metrics"),
    ]

    operations = [
        migrations.CreateModel(
            name="MLMetrics",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True)),
                ("total_requests", models.IntegerField(default=0)),
                ("intent_accuracy", models.FloatField(blank=True, null=True)),
                ("average_latency_ms", models.FloatField(blank=True, null=True)),
                ("error_rate", models.FloatField(blank=True, null=True)),
                ("intent_breakdown", models.JSONField(blank=True, default=dict)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
