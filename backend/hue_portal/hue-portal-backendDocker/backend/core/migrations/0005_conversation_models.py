"""
Migration to add ConversationSession and ConversationMessage models.
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_add_embeddings"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversationSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("user_id", models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Conversation Session",
                "verbose_name_plural": "Conversation Sessions",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="ConversationMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "User"), ("bot", "Bot")], max_length=10)),
                ("content", models.TextField()),
                ("intent", models.CharField(blank=True, max_length=50, null=True)),
                ("entities", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="core.conversationsession")),
            ],
            options={
                "verbose_name": "Conversation Message",
                "verbose_name_plural": "Conversation Messages",
                "ordering": ["timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="conversationsession",
            index=models.Index(fields=["session_id"], name="core_conver_session_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationsession",
            index=models.Index(fields=["user_id", "-updated_at"], name="core_conver_user_id_updated_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationmessage",
            index=models.Index(fields=["session", "timestamp"], name="core_conver_session_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationmessage",
            index=models.Index(fields=["session", "role", "timestamp"], name="core_conver_session_role_timestamp_idx"),
        ),
    ]

