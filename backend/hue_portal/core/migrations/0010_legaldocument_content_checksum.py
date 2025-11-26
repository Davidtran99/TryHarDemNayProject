from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_ingestionjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="legaldocument",
            name="content_checksum",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]

