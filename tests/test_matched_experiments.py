import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ead_dc_fl.matched_experiments import (
    aggregate_models, array_sha256, canonical_sha256, file_sha256,
    load_matched_experiment, local_training_order, restore_initial_models,
)

spec = importlib.util.spec_from_file_location("matched_run_checker", ROOT / "scripts/check_matched_run_inputs.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class AggregationTests(unittest.TestCase):
    def test_unequal_client_sizes_are_sample_weighted(self):
        a = [np.array([1., 9.], np.float32), np.array([[2.]], np.float32)]
        b = [np.array([3., 5.], np.float32), np.array([[6.]], np.float32)]
        result = aggregate_models([a, b], [1, 3])
        np.testing.assert_array_equal(result[0], [2.5, 6.])
        np.testing.assert_array_equal(result[1], [[5.]])
        self.assertEqual(result[0].dtype, np.float32)
        np.testing.assert_array_equal(a[0], [1., 9.])

    def test_filtering_renormalises_over_survivors_only(self):
        uploads = [[np.array([v], np.float32)] for v in [1., 3., 1000.]]
        accepted = [0, 1]
        result = aggregate_models([uploads[i] for i in accepted], [1, 3])
        np.testing.assert_array_equal(result[0], [2.5])
        single = aggregate_models([uploads[1]], [3])
        np.testing.assert_array_equal(single[0], [3.])
        self.assertFalse(np.shares_memory(single[0], uploads[1][0]))

    def test_median_stays_unweighted(self):
        uploads = [[np.array([1., 9.], np.float32)], [np.array([3., 5.], np.float32)]]
        np.testing.assert_array_equal(aggregate_models(uploads, [1, 100], "median")[0], [2., 7.])

    def test_reject_invalid_inputs(self):
        a = [np.array([1.], np.float32)]
        for counts in ([0], [-1], [True], [1.5]):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                aggregate_models([a], counts)
        with self.assertRaises(ValueError):
            aggregate_models([], [])
        with self.assertRaises(ValueError):
            aggregate_models([a, [np.array([1., 2.], np.float32)]], [1, 1])
        with self.assertRaises(ValueError):
            aggregate_models([a, [np.array([1.], np.float64)]], [1, 1])
        with self.assertRaises(ValueError):
            aggregate_models([[np.array([np.nan], np.float32)]], [1])


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.directory = self.root / "shared"
        self.directory.mkdir()
        self.clients = {"clients": [{"client_id": 0, "architecture": "small"}]}
        path = self.root / "clients.json"
        path.write_text(json.dumps(self.clients))
        value = np.array([1., 2.], np.float32)
        np.savez(self.directory / "small.npz", tensor_00=value)
        self.manifest = {
            "schema": "matched_development_v1", "seed": 42, "rounds": 2,
            "training_settings": {"batch": 128}, "architectures": ["small"],
            "client_manifest": "clients.json", "input_sha256": {"clients.json": file_sha256(path)},
            "initial_models": {"small": {"file": "small.npz", "sha256": file_sha256(self.directory / "small.npz"),
                                         "keys": ["tensor_00"], "tensor_sha256": [array_sha256(value)]}},
            "participation": {"1": {"small": [0]}, "2": {"small": [0]}},
        }
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        payload = {key: value for key, value in self.manifest.items() if key != "experiment_id"}
        self.manifest["experiment_id"] = canonical_sha256(payload)
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest))

    def load(self):
        return load_matched_experiment(self.directory, 42, 2, {"batch": 128}, self.root)

    def test_valid_contract_and_exact_restore(self):
        class Model:
            def set_weights(self, values):
                self.values = [value.copy() for value in values]
            def get_weights(self):
                return self.values
        model = Model()
        first = self.load()
        hashes = restore_initial_models({"small": model}, first, self.directory)
        np.testing.assert_array_equal(model.get_weights()[0], [1., 2.])
        self.assertEqual(hashes["small"], first["initial_models"]["small"]["tensor_sha256"])

    def test_input_mutation_fails_before_training(self):
        (self.root / "clients.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.load()

    def test_initial_checkpoint_mutation_fails(self):
        np.savez(self.directory / "small.npz", tensor_00=np.array([9., 2.], np.float32))
        with self.assertRaisesRegex(ValueError, "checkpoint changed"):
            self.load()

    def test_changed_manifest_and_training_budget_fail(self):
        self.manifest["seed"] = 43
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "manifest was changed"):
            self.load()
        self.save()
        with self.assertRaisesRegex(ValueError, "seed/rounds"):
            self.load()
        self.manifest["seed"] = 42
        self.save()
        with self.assertRaisesRegex(ValueError, "Training settings"):
            load_matched_experiment(self.directory, 42, 2, {"batch": 64}, self.root)

    def test_unexpected_participant_fails(self):
        self.manifest["participation"]["2"]["small"] = [1]
        self.save()
        with self.assertRaisesRegex(ValueError, "same full cohort"):
            self.load()

    def test_orders_independent_of_unrelated_rng_draws(self):
        a = local_training_order(100, 1043)
        np.random.seed(1)
        np.random.normal(size=1000)
        b = local_training_order(100, 1043)
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.array_equal(a, local_training_order(100, 1044)))


class ReportTests(unittest.TestCase):
    def report(self):
        participants = {"small": [0]}
        return {"status": "completed", "matched_experiment_id": "id", "initial_state_sha256": {"small": ["sha"]},
                "seed": 42, "planned_rounds": 1, "training_settings": {}, "execution_environment": {},
                "source_sha256": "source", "client_manifest_sha256": "clients",
                "master_weights_sha256": "master", "models_and_kd_sha256": "models",
                "rounds": [{"round": 1, "participation": participants,
                            "participation_sha256": canonical_sha256(participants),
                            "clusters": {"small": {"client_ids": [0], "local_training_order_sha256": {"0": "order"}}}}]}

    def test_method_outcomes_can_differ_but_input_changes_do_not_match(self):
        a = self.report()
        b = copy.deepcopy(a)
        b["aggregation"] = "sample_weighted_fedavg"
        b["rounds"][0]["clusters"]["small"]["post_kd_validation"] = {"accuracy": .1}
        self.assertEqual(checker.fingerprint(a), checker.fingerprint(b))
        b["initial_state_sha256"]["small"] = ["different"]
        self.assertNotEqual(checker.fingerprint(a), checker.fingerprint(b))

    def test_partial_or_inconsistent_reports_fail(self):
        a = self.report()
        a["status"] = "running"
        with self.assertRaises(ValueError):
            checker.fingerprint(a)
        a = self.report()
        a["rounds"][0]["clusters"]["small"]["client_ids"] = [1]
        with self.assertRaises(ValueError):
            checker.fingerprint(a)


if __name__ == "__main__":
    unittest.main()
