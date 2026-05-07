from django.test import SimpleTestCase

from gui.recommendations.heuristics import can_emit_ml_recommendation


class RecommendationHeuristicTests(SimpleTestCase):
    def test_ml_recommendation_requires_minimum_data_window(self):
        self.assertFalse(can_emit_ml_recommendation(29, 100))

    def test_ml_recommendation_requires_minimum_event_count(self):
        self.assertFalse(can_emit_ml_recommendation(60, 49))

    def test_ml_recommendation_is_enabled_at_minimum_threshold(self):
        self.assertTrue(can_emit_ml_recommendation(30, 50))
