from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_legal_upload_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="legaldocument",
            name="raw_text_ocr",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="legalsection",
            name="is_ocr",
            field=models.BooleanField(default=False),
        ),
    ]

