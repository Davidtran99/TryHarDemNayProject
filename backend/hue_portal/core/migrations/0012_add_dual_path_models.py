"""
Migration to add Dual-Path RAG models: GoldenQuery and QueryRoutingLog.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_alter_mlmetrics_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="GoldenQuery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.TextField(db_index=True, unique=True)),
                ("query_normalized", models.TextField(db_index=True)),
                ("query_embedding", models.JSONField(blank=True, null=True)),
                ("intent", models.CharField(db_index=True, max_length=50)),
                ("response_message", models.TextField()),
                ("response_data", models.JSONField()),
                ("verified_by", models.CharField(max_length=100)),
                ("verified_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("usage_count", models.IntegerField(default=0)),
                ("accuracy_score", models.FloatField(default=1.0)),
                ("version", models.IntegerField(default=1)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "verbose_name": "Golden Query",
                "verbose_name_plural": "Golden Queries",
                "ordering": ["-usage_count", "-verified_at"],
            },
        ),
        migrations.CreateModel(
            name="QueryRoutingLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.TextField()),
                ("route", models.CharField(db_index=True, max_length=20)),
                ("router_confidence", models.FloatField()),
                ("router_method", models.CharField(db_index=True, max_length=20)),
                ("matched_golden_query_id", models.IntegerField(blank=True, null=True)),
                ("similarity_score", models.FloatField(blank=True, null=True)),
                ("response_time_ms", models.IntegerField()),
                ("intent", models.CharField(blank=True, db_index=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "verbose_name": "Query Routing Log",
                "verbose_name_plural": "Query Routing Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="goldenquery",
            index=models.Index(fields=["query_normalized", "intent"], name="core_golden_query_normalized_intent_idx"),
        ),
        migrations.AddIndex(
            model_name="goldenquery",
            index=models.Index(fields=["is_active", "intent"], name="core_golden_query_active_intent_idx"),
        ),
        migrations.AddIndex(
            model_name="goldenquery",
            index=models.Index(fields=["usage_count"], name="core_golden_query_usage_count_idx"),
        ),
        migrations.AddIndex(
            model_name="queryroutinglog",
            index=models.Index(fields=["route", "created_at"], name="core_query_routing_route_created_idx"),
        ),
        migrations.AddIndex(
            model_name="queryroutinglog",
            index=models.Index(fields=["router_method", "created_at"], name="core_query_routing_method_created_idx"),
        ),
        migrations.AddIndex(
            model_name="queryroutinglog",
            index=models.Index(fields=["intent", "created_at"], name="core_query_routing_intent_created_idx"),
        ),
    ]

