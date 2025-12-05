from types import SimpleNamespace
from django.test import SimpleTestCase

from hue_portal.core.hybrid_search import calculate_exact_match_boost, _sort_by_exact_match


class HybridExactBoostTests(SimpleTestCase):
    def test_boost_detects_phrase(self):
        section = SimpleNamespace(section_title="Xử lý kỷ luật", name="Xử lý kỷ luật cán bộ")
        boost = calculate_exact_match_boost(section, "kỷ luật cán bộ", ["section_title", "name"])
        self.assertGreaterEqual(boost, 0.5)

    def test_sort_prioritizes_exact_match(self):
        obj_exact = object()
        obj_regular = object()
        filtered = [(obj_regular, 0.9), (obj_exact, 0.4)]
        boosts = {obj_exact: 0.85, obj_regular: 0.05}
        sorted_scores = _sort_by_exact_match(filtered, boosts)
        self.assertIs(sorted_scores[0][0], obj_exact)

