from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_legalsection_excerpt_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="legalsection",
                    name="is_ocr",
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]

