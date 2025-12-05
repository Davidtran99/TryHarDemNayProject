from django.test import SimpleTestCase

from hue_portal.chatbot.router import IntentRoute, decide_route


class RouterDecisionTests(SimpleTestCase):
    def test_simple_greeting_routed_to_greeting(self):
        decision = decide_route("chào bạn", "greeting", 0.9)
        self.assertEqual(decision.route, IntentRoute.GREETING)
        self.assertEqual(decision.forced_intent, "greeting")

    def test_doc_code_forces_search_legal(self):
        decision = decide_route("Cho tôi xem quyết định 69 nói gì", "general_query", 0.4)
        self.assertEqual(decision.route, IntentRoute.SEARCH)
        self.assertEqual(decision.forced_intent, "search_legal")

    def test_low_confidence_goes_to_small_talk(self):
        decision = decide_route("tôi mệt quá", "general_query", 0.2)
        self.assertEqual(decision.route, IntentRoute.SMALL_TALK)
        self.assertEqual(decision.forced_intent, "general_query")

    def test_confident_fine_query_stays_search(self):
        decision = decide_route("mức phạt vượt đèn đỏ là gì", "search_fine", 0.92)
        self.assertEqual(decision.route, IntentRoute.SEARCH)
        self.assertIsNone(decision.forced_intent)

    def test_small_talk_routes_to_small_talk(self):
        decision = decide_route("mệt quá hôm nay", "general_query", 0.4)
        self.assertEqual(decision.route, IntentRoute.SMALL_TALK)
        self.assertEqual(decision.forced_intent, "general_query")

    def test_keyword_override_forces_fine_intent(self):
        decision = decide_route("phạt vượt đèn đỏ sao vậy", "general_query", 0.5)
        self.assertEqual(decision.route, IntentRoute.SEARCH)
        self.assertEqual(decision.forced_intent, "search_fine")

    def test_keyword_override_forces_procedure_intent(self):
        decision = decide_route("thủ tục cư trú cần hồ sơ gì", "general_query", 0.5)
        self.assertEqual(decision.route, IntentRoute.SEARCH)
        self.assertEqual(decision.forced_intent, "search_procedure")

