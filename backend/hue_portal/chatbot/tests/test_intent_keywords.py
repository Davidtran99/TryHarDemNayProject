import unittest

from hue_portal.chatbot.chatbot import Chatbot


class IntentKeywordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = Chatbot()

    def test_office_keywords_have_priority(self):
        intent, confidence = self.bot.classify_intent("Cho mình địa chỉ Công an phường An Cựu", context=None)
        self.assertEqual(intent, "search_office")
        self.assertGreaterEqual(confidence, 0.7)

    def test_document_code_forces_search_legal(self):
        intent, confidence = self.bot.classify_intent("Quyết định 69 quy định gì về kỷ luật?", context=None)
        self.assertEqual(intent, "search_legal")
        self.assertGreaterEqual(confidence, 0.8)

    def test_fine_keywords_override_greeting(self):
        intent, confidence = self.bot.classify_intent("Chào bạn mức phạt vượt đèn đỏ là bao nhiêu", context=None)
        self.assertEqual(intent, "search_fine")
        self.assertGreaterEqual(confidence, 0.8)


if __name__ == "__main__":
    unittest.main()

