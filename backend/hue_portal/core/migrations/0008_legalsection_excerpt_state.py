from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_add_legal_indexes"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="legalsection",
                    name="excerpt",
                    field=models.TextField(blank=True, default=""),
                ),
            ],
        ),
    ]

