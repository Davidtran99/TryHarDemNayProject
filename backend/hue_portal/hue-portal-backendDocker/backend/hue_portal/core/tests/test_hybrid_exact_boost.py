import unittest
from types import SimpleNamespace

from hue_portal.core.hybrid_search import calculate_exact_match_boost, _sort_by_exact_match


class HybridSearchExactMatchTests(unittest.TestCase):
    def test_document_code_boost(self):
        section = SimpleNamespace(
            section_title="Điều 5",
            section_code="Điều 5",
            document=SimpleNamespace(code="QD-69-TW"),
        )
        boost = calculate_exact_match_boost(section, "theo quyết định 69", ["section_title"])
        self.assertGreaterEqual(boost, 0.6)

    def test_sort_promotes_exact_match(self):
        obj_exact = object()
        obj_regular = object()
        filtered = [(obj_regular, 0.9), (obj_exact, 0.4)]
        boosts = {obj_exact: 0.85, obj_regular: 0.0}

        sorted_scores = _sort_by_exact_match(filtered, boosts)
        self.assertIs(sorted_scores[0][0], obj_exact)


if __name__ == "__main__":
    unittest.main()

