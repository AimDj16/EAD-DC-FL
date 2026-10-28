"""Integrity and metric checks that run without TensorFlow or project data."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

path = Path(__file__).resolve().parents[1] / "scripts" / "audit_server_supervision.py"
spec = importlib.util.spec_from_file_location("server_audit", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.parts = dict(client_training=np.array([0]), server_kd=np.array([1]),
                          server_validation=np.array([2]), test=np.array([3]))

    def test_disjoint_rows_and_groups(self):
        result = audit.check_split_boundaries(self.parts, np.arange(4), 4)
        self.assertEqual(len(result), 6)
        self.assertTrue(all(value == 0 for value in result.values()))

    def test_feature_overlap_rejected_despite_disjoint_row_ids(self):
        with self.assertRaisesRegex(ValueError, "Feature groups"):
            audit.check_split_boundaries(self.parts, np.array([0, 0, 1, 2]), 4)

    def test_duplicate_or_missing_row_rejected(self):
        self.parts["test"] = np.array([2])
        with self.assertRaisesRegex(ValueError, "every row"):
            audit.check_split_boundaries(self.parts, np.arange(4), 4)

    def test_training_fit_accepted_but_whole_file_fit_rejected(self):
        training = np.array([[1., 5.], [3., 5.], [5., 5.]])
        def saved(values):
            scaler = StandardScaler().fit(values)
            return dict(mean=scaler.mean_, scale=scaler.scale_, variance=scaler.var_, samples_seen=scaler.n_samples_seen_)
        audit.check_training_normalisation(training, saved(training))
        with self.assertRaisesRegex(ValueError, "client-training-only"):
            audit.check_training_normalisation(training, saved(np.vstack([training, [100., 50.]])))


class MetricTests(unittest.TestCase):
    def test_targeted_error_and_ids_false_alarm_use_distinct_denominators(self):
        metrics = audit.metrics_from_predictions(np.array([0, 0, 1, 1, 2]),
            np.array([0, 1, 0, 1, 2]), ["Normal", "Malware", "DoS"])
        self.assertEqual(metrics["targeted_hits"], 1)
        self.assertEqual(metrics["targeted_source_rows"], 2)
        self.assertEqual(metrics["targeted_misclassification_rate"], 0.5)
        self.assertEqual(metrics["normal_false_alarm_rate"], 0.5)
        self.assertEqual(metrics["confusion_matrix"], [[1, 1, 0], [1, 1, 0], [0, 0, 1]])

    def test_missing_source_or_invalid_prediction_rejected(self):
        for y, pred in [(np.array([0, 0]), np.array([0, 0])),
                        (np.array([0, 1]), np.array([0, 2]))]:
            with self.assertRaises(ValueError):
                audit.metrics_from_predictions(y, pred, ["Normal", "Malware"])


if __name__ == "__main__":
    unittest.main()
