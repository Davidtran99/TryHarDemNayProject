from django.test import SimpleTestCase

from hue_portal.core.rag import retrieve_top_k_documents


class RetrieveGeneralIntentTests(SimpleTestCase):
    def test_general_content_type_returns_empty(self):
        docs = retrieve_top_k_documents("xin chào", "general", top_k=3)
        self.assertEqual(docs, [])

