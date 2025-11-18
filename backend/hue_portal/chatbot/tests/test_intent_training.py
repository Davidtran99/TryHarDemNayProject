import json
from pathlib import Path
import unittest

from hue_portal.chatbot.training import train_intent


class IntentTrainingTestCase(unittest.TestCase):
    def test_train_pipeline_produces_artifacts(self):
        model_path, metrics_path, metrics = train_intent.train(train_intent.DEFAULT_DATASET, test_size=0.3, random_state=123)

        self.assertTrue(model_path.exists(), "Model artifact should be created")
        self.assertTrue(metrics_path.exists(), "Metrics file should be created")

        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        self.assertIn("accuracy", payload)
        self.assertGreaterEqual(payload["accuracy"], 0.0)
        self.assertLessEqual(payload["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
