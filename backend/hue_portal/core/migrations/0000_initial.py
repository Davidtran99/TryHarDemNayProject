"""
Initial migration to create base models.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Procedure",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=500)),
                ("domain", models.CharField(db_index=True, max_length=100)),
                ("level", models.CharField(blank=True, max_length=50)),
                ("conditions", models.TextField(blank=True)),
                ("dossier", models.TextField(blank=True)),
                ("fee", models.CharField(blank=True, max_length=200)),
                ("duration", models.CharField(blank=True, max_length=200)),
                ("authority", models.CharField(blank=True, max_length=300)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Fine",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=500)),
                ("article", models.CharField(blank=True, max_length=100)),
                ("decree", models.CharField(blank=True, max_length=100)),
                ("min_fine", models.DecimalField(blank=True, decimal_places=0, max_digits=12, null=True)),
                ("max_fine", models.DecimalField(blank=True, decimal_places=0, max_digits=12, null=True)),
                ("license_points", models.CharField(blank=True, max_length=50)),
                ("remedial", models.TextField(blank=True)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name="Office",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_name", models.CharField(max_length=300)),
                ("address", models.CharField(blank=True, max_length=500)),
                ("district", models.CharField(blank=True, db_index=True, max_length=100)),
                ("working_hours", models.CharField(blank=True, max_length=200)),
                ("phone", models.CharField(blank=True, max_length=100)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("service_scope", models.CharField(blank=True, max_length=300)),
            ],
        ),
        migrations.CreateModel(
            name="Advisory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=500)),
                ("summary", models.TextField()),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("published_at", models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Synonym",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keyword", models.CharField(max_length=120, unique=True)),
                ("alias", models.CharField(max_length=120)),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("path", models.CharField(max_length=300)),
                ("query", models.CharField(blank=True, max_length=500)),
                ("status", models.IntegerField(default=200)),
            ],
        ),
    ]

