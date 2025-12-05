"""Smoke tests to ensure chatbot + essential management commands work."""

from __future__ import annotations

from django.core.management import call_command, load_command_class
from django.test import TestCase

from hue_portal.chatbot.chatbot import get_chatbot


class ChatbotSmokeTests(TestCase):
    """Verify chatbot core components can initialize without errors."""

    def test_chatbot_initializes_once(self) -> None:
        bot = get_chatbot()
        self.assertIsNotNone(bot)
        # Intent classifier should be available after initialization/training
        self.assertIsNotNone(bot.intent_classifier)


class ManagementCommandSmokeTests(TestCase):
    """Ensure critical management commands are wired correctly."""

    def test_django_check_command(self) -> None:
        call_command("check")

    def test_retry_ingestion_command_loads(self) -> None:
        load_command_class("hue_portal.core", "retry_ingestion_job")

