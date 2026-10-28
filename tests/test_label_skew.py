"""Exact allocation margins, fixed identities, training-only preparation and audits."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ead_dc_fl.matched_experiments import array_sha256, canonical_sha256, file_sha256
from ead_dc_fl.label_skew import (
    ALLOCATION_VERSION, ARCHITECTURES, TRAINING_SETTINGS, balanced_class_counts,
    class_distribution_metrics, ids_metrics, check_metric_counts, make_allocation,
    poison_opportunities, validate_completed_run, verify_allocation, verify_subset_record,
)

CLASSES = ["DoS", "Injection", "MITM", "Malware", "Normal", "Routing", "Vulnerability_Analysis"]
MALICIOUS = [0, 2, 11, 15, 16, 24, 25, 26, 28]


def allocation_fixture():
    original = {f"client_{cid:02d}": np.arange(cid*140, (cid+1)*140, dtype=np.int64) for cid in range(30)}
    labels = np.tile(np.arange(7), 600)
    members = {name: list(range(index, 30, 3)) for index, name in enumerate(ARCHITECTURES)}
    return original, labels, members


def metric_fixture():
    labels = np.repeat(np.arange(7), [3185, 102, 450, 801, 801, 657, 1604])
    predictions = labels.copy()
    predictions[np.flatnonzero(labels == 3)[:3]] = 4
    predictions[np.flatnonzero(labels == 4)[:2]] = 0
    value = ids_metrics(labels, predictions, CLASSES)
    value.update({"accuracy": float(accuracy_score(labels, predictions)),
                  "macro_f1": float(f1_score(labels, predictions, average="macro")),
                  "targeted_hits": 3, "targeted_source_rows": 801,
                  "targeted_misclassification_rate": 3/801,
                  "per_class_recall": dict(zip(CLASSES, recall_score(labels, predictions, average=None)))})
    return value


class AllocatorTests(unittest.TestCase):
    def test_exact_margins_with_zero_class_and_unequal_clients(self):
        for seed in range(25):
            rows = np.array([100, 0, 37, 63])
            capacities = np.array([31, 41, 58, 70])
            value, _ = balanced_class_counts(rows, capacities, 0.5, seed)
            np.testing.assert_array_equal(value.sum(axis=1), rows)
            np.testing.assert_array_equal(value.sum(axis=0), capacities)
            self.assertTrue((value >= 0).all())

    def test_one_class_and_tiny_integer_pools(self):
        for rows, capacities in [(np.array([5]), np.array([2, 3])),
                                 (np.array([1, 2]), np.array([1, 1, 1]))]:
            value, _ = balanced_class_counts(rows, capacities, 0.5, 42)
            np.testing.assert_array_equal(value.sum(axis=1), rows)
            np.testing.assert_array_equal(value.sum(axis=0), capacities)

    def test_invalid_inputs_fail(self):
        cases = [(np.array([2]), np.array([3]), .5), (np.array([-1, 3]), np.array([2]), .5),
                 (np.array([2]), np.array([0, 2]), .5), (np.array([2.0]), np.array([2]), .5),
                 (np.array([2]), np.array([2]), 0), (np.array([2]), np.array([2]), float("nan"))]
        for rows, capacities, alpha in cases:
            with self.assertRaises(ValueError):
                balanced_class_counts(rows, capacities, alpha, 42)

    def test_rows_capacities_architecture_pools_and_training_only_access(self):
        original, labels, members = allocation_fixture()
        # Outside-training rows carry invalid labels and must never be accessed.
        labels = np.concatenate([labels, np.array([-99, -99])])
        changed, report = make_allocation(original, labels, members, 7)
        verify_allocation(original, changed, labels, members, 7)
        for name in ARCHITECTURES:
            self.assertGreater(report[name]["labelskew"]["mean_total_variation"], .10)
            self.assertAlmostEqual(report[name]["iid"]["mean_total_variation"], 0)
        for key in original:
            self.assertEqual(len(original[key]), len(changed[key]))

    def test_allocation_stream_is_independent_of_global_numpy_draws(self):
        original, labels, members = allocation_fixture()
        left, _ = make_allocation(original, labels, members, 7)
        np.random.seed(99)
        np.random.random(1000)
        right, _ = make_allocation(original, labels, members, 7)
        for key in original:
            np.testing.assert_array_equal(left[key], right[key])

    def test_row_duplication_pool_change_and_capacity_change_rejected(self):
        original, labels, members = allocation_fixture()
        changed, _ = make_allocation(original, labels, members, 7)
        bad = {k: v.copy() for k, v in changed.items()}
        bad["client_00"][0] = bad["client_01"][0]
        with self.assertRaisesRegex(ValueError, "exactly once"):
            verify_allocation(original, bad, labels, members, 7)
        bad = {k: v.copy() for k, v in changed.items()}
        bad["client_00"][0], bad["client_01"][0] = bad["client_01"][0], bad["client_00"][0]
        with self.assertRaisesRegex(ValueError, "Architecture"):
            verify_allocation(original, bad, labels, members, 7)
        bad = {k: v.copy() for k, v in changed.items()}
        bad["client_00"] = np.append(bad["client_00"], bad["client_03"][0])
        bad["client_03"] = bad["client_03"][1:]
        with self.assertRaisesRegex(ValueError, "capacity"):
            verify_allocation(original, bad, labels, members, 7)

    def test_zero_attack_opportunity_does_not_move_identity(self):
        labels = np.array([0, 0, 3, 4])
        allocations = {"client_00": np.array([0, 1]), "client_01": np.array([2, 3])}
        poison = poison_opportunities(allocations, labels, [0], 3)
        self.assertEqual(list(poison), ["client_00"])
        self.assertEqual(len(poison["client_00"]), 0)

    def test_metrics_have_distinct_targeted_and_normal_denominators(self):
        value = metric_fixture()
        check_metric_counts(value)
        self.assertEqual(value["targeted_hits"], 3)
        self.assertAlmostEqual(value["normal_false_alarm_rate"], 2/801)
        value["macro_f1"] -= .1
        with self.assertRaisesRegex(ValueError, "macro_f1"):
            check_metric_counts(value)

    def test_replay_allows_only_additional_diagnostics_not_changed_values(self):
        reference = {"kd": {"accepted": True}, "uploads": [{"poisoning_applied": False}]}
        current = {"kd": {"accepted": True, "diagnostic": 1},
                   "uploads": [{"poisoning_applied": False, "new_hash": "x"}]}
        verify_subset_record(current, reference)
        current["kd"]["accepted"] = False
        with self.assertRaises(ValueError):
            verify_subset_record(current, reference)


class PreparationPipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        original, labels, members = allocation_fixture()
        self.original, self.labels, self.members = original, labels, members
        def directory(path):
            value = self.root/path
            value.mkdir(parents=True, exist_ok=True)
            return value
        def write(path, value):
            (self.root/path).write_text(json.dumps(value))
        source = directory(Path("data/raw/idsiot2024"))/"Process_1 IDS-IoT-2024.csv"
        pd.DataFrame({"Attack_Category_x": [CLASSES[y] for y in labels] + ["OUTSIDE_TRAINING_UNUSED"]*14}).to_csv(source, index=False)
        partition = directory(Path("data/partitions/idsiot2024/candidate_seed42_groups2"))
        np.savez_compressed(partition/"indices.npz", client_training=np.arange(4200), server_kd=np.arange(4200,4207),
                            server_validation=np.arange(4207,4210), test=np.arange(4210,4214))
        write(partition.relative_to(self.root)/"manifest.json", {"classes": CLASSES, "protocol": {"target_column": "Attack_Category_x"}})
        clients = directory(Path("data/clients/idsiot2024/development_iid_seed42"))
        np.savez_compressed(clients/"client_indices.npz", **original)
        np.savez_compressed(clients/"normalisation.npz", mean=np.array([0.]), scale=np.array([1.]))
        client_manifest = {"classes": CLASSES, "feature_names": ["f0"], "checks": {"all_classes_present_in_every_client": True},
                           "clients": [{"client_id": cid, "architecture": ARCHITECTURES[cid%3], "rows": 140,
                                        "class_counts": {name: 20 for name in CLASSES}} for cid in range(30)]}
        write(clients.relative_to(self.root)/"manifest.json", client_manifest)
        attacks = directory(Path("data/attacks/idsiot2024/malware_to_normal_seed142"))
        write(attacks.relative_to(self.root)/"protocol.json", {
            "attack": "targeted_label_flipping", "source_class": "Malware", "destination_class": "Normal",
            "source_class_id": 3, "destination_class_id": 4, "malicious_client_ids": MALICIOUS,
            "clients": [{"client_id": cid, "poisoned_rows": 20} for cid in MALICIOUS]})
        for path in ["src/ead_dc_fl/label_skew.py", "scripts/run_labelskew_development.py", "scripts/run_labelskew_batch.py",
                     "scripts/check_matched_run_inputs.py", "docs/labelskew_development_protocol.md"]:
            parent = directory(Path(path).parent)
            shutil.copyfile(ROOT/path, self.root/path)
        paths = [source, partition/"indices.npz", partition/"manifest.json", clients/"client_indices.npz",
                 clients/"normalisation.npz", clients/"manifest.json", attacks/"protocol.json"]
        for seed in [42,2026,31415]:
            output = directory(Path(f"data/experiments/idsiot2024/replication_seed{seed}_rounds12_v1"))
            initial = {}
            for name in ARCHITECTURES:
                filename = name+"_initial_weights.npz"
                tensor = np.array([float(seed)], dtype=np.float32)
                np.savez_compressed(output/filename, tensor_00=tensor)
                initial[name] = {"file": filename, "sha256": file_sha256(output/filename), "keys": ["tensor_00"],
                                 "tensor_sha256": [array_sha256(tensor)]}
            manifest = {"schema": "matched_development_v1", "seed": seed, "rounds": 12,
                "architectures": list(ARCHITECTURES), "initial_models": initial,
                "input_sha256": {p.relative_to(self.root).as_posix(): file_sha256(p) for p in paths},
                "training_settings": TRAINING_SETTINGS, "client_manifest": (clients/"manifest.json").relative_to(self.root).as_posix(),
                "client_sample_counts": {key: len(rows) for key, rows in original.items()},
                "participation": {str(n): members for n in range(1,13)}, "participation_policy": "full_participation_fixed_order"}
            manifest["experiment_id"] = canonical_sha256(manifest)
            (output/"manifest.json").write_text(json.dumps(manifest))

    def execute(self):
        return subprocess.run([sys.executable, str(ROOT/"scripts/prepare_labelskew_development.py")],
                              cwd=self.root, text=True, capture_output=True)

    def test_preparation_is_training_only_preserves_inputs_and_reuses(self):
        source = self.root/"data/clients/idsiot2024/development_iid_seed42/client_indices.npz"
        before = source.read_bytes()
        first = self.execute()
        self.assertEqual(first.returncode, 0, first.stderr+first.stdout)
        second = self.execute()
        self.assertEqual(second.returncode, 0, second.stderr+second.stdout)
        self.assertIn("REUSE VERIFIED", second.stdout)
        self.assertEqual(before, source.read_bytes())
        new = self.root/"data/clients/idsiot2024/development_labelskew_a0p5_alloc42_v1"
        report = json.loads((new/"preparation_report.json").read_text())
        self.assertFalse(report["training_performed"])
        self.assertFalse(report["test_evaluated"])
        self.assertTrue(report["quality_passed"])
        with np.load(new/"client_indices.npz") as saved:
            changed = {key: saved[key] for key in saved.files}
        verify_allocation(self.original, changed, self.labels, self.members, 7)
        self.assertEqual((new/"normalisation.npz").read_bytes(), (source.parent/"normalisation.npz").read_bytes())

    def test_registered_allocation_tampering_fails_without_regeneration(self):
        first = self.execute()
        self.assertEqual(first.returncode, 0, first.stderr+first.stdout)
        path = self.root/"data/clients/idsiot2024/development_labelskew_a0p5_alloc42_v1/client_indices.npz"
        path.write_bytes(b"tampered")
        second = self.execute()
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("Matched input changed", second.stderr)
        self.assertEqual(path.read_bytes(), b"tampered")


class CompletedRunAuditTests(unittest.TestCase):
    def setUp(self):
        manifest = {"experiment_id": "fixture", "seed": 42, "initial_models": {
            name: {"tensor_sha256": [name+"_initial"]} for name in ARCHITECTURES},
            "client_manifest": "clients.json", "input_sha256": {
                path: path+"_sha" for path in ["scripts/run_labelskew_development.py", "src/ead_dc_fl/label_skew.py",
                    "clients.json", "data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv",
                    "outputs/development/master_pretrain_seed42/master_weights.npz",
                    "src/ead_dc_fl/models_and_kd.py", "src/ead_dc_fl/attacks.py"]},
            "client_sample_counts": {f"client_{cid:02d}": 100 for cid in range(30)},
            "participation": {str(n): {name: list(range(j,30,3)) for j,name in enumerate(ARCHITECTURES)} for n in range(1,13)}}
        self.manifest = manifest
        self.selection = {"malicious_client_ids": MALICIOUS,
                          "clients": [{"client_id": cid, "poisoned_rows": 0 if cid == 24 else 2} for cid in MALICIOUS]}
        report = {"status": "completed", "configuration_id": "matched_labelskew_development_v1",
            "data_regime": "labelskew", "scientific_run_count": 1, "seed": 42, "planned_rounds": 12,
            "contract_rounds": 12, "matched_experiment_id": "fixture", "mode": "original",
            "ead_enabled": False, "kd_enabled": True, "arm": "attack", "aggregation": "sample_weighted_fedavg",
            "training_settings": TRAINING_SETTINGS, "allocation_version": ALLOCATION_VERSION,
            "allocation_seed": 42, "dirichlet_alpha": .5,
            "initial_state_sha256": {name: entry["tensor_sha256"] for name,entry in manifest["initial_models"].items()},
            "client_manifest_sha256": manifest["input_sha256"]["clients.json"],
            "source_sha256": manifest["input_sha256"]["data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv"],
            "master_weights_sha256": manifest["input_sha256"]["outputs/development/master_pretrain_seed42/master_weights.npz"],
            "models_and_kd_sha256": manifest["input_sha256"]["src/ead_dc_fl/models_and_kd.py"],
            "attack_operator_sha256": manifest["input_sha256"]["src/ead_dc_fl/attacks.py"],
            "script_sha256": manifest["input_sha256"]["scripts/run_labelskew_development.py"],
            "label_skew_module_sha256": manifest["input_sha256"]["src/ead_dc_fl/label_skew.py"],
            "test_evaluated": False, "final_protocol_frozen": False, "preprocessing_provenance_verified": False,
            "rounds": []}
        metric = metric_fixture()
        for number in range(1,13):
            record = {"round": number, "teacher": "master" if number <= 3 else "small",
                      "participation": manifest["participation"][str(number)], "clusters": {}}
            for name, ids in record["participation"].items():
                designated = set(ids) & set(MALICIOUS)
                effective = designated - {24}
                uploads = [{"client_id": cid, "designated_malicious_client": cid in designated,
                            "poisoning_applied": cid in effective, "poisoned_label_rows": 2 if cid in effective else 0,
                            "source_class_rows_available": 0 if cid == 24 else 2,
                            "training_labels_original_sha256": "before",
                            "training_labels_used_sha256": "after" if cid in effective else "before"} for cid in ids]
                decision = {"performed": True, "candidate_validation": metric, "accepted": True}
                if number > 3 and name == "small":
                    decision = {"performed": False, "reason": "teacher_self_distillation"}
                record["clusters"][name] = {
                    "client_ids": ids, "rejected_client_ids": [], "retained_previous_model": False,
                    "accepted_count": 10, "accepted_sample_counts": {str(cid): 100 for cid in ids},
                    "fedavg_coefficients": {str(cid): .1 for cid in ids}, "upload_diagnostics": uploads,
                    "pre_kd_validation": metric, "post_kd_validation": metric, "kd": decision,
                    "screening_audit": {"malicious_rejected": [], "malicious_accepted": sorted(designated), "benign_rejected": []},
                    "effective_poisoning_screening_audit": {
                        "effective_poisoned_client_ids": sorted(effective), "effective_poisoned_rejected": [],
                        "effective_poisoned_accepted": sorted(effective),
                        "designated_zero_opportunity_client_ids": sorted(designated - effective),
                        "total_poisoned_label_rows": 2*len(effective)}}
            report["rounds"].append(record)
        self.report = copy.deepcopy(report)

    def test_valid_full_report_with_zero_opportunity_designated_client(self):
        validate_completed_run(self.report, self.manifest, "attack", "off", "on", self.selection)

    def test_claiming_no_op_client_was_poisoned_fails(self):
        upload = next(u for u in self.report["rounds"][0]["clusters"]["small"]["upload_diagnostics"] if u["client_id"] == 24)
        upload["poisoning_applied"] = True
        with self.assertRaisesRegex(ValueError, "Poison execution"):
            validate_completed_run(self.report, self.manifest, "attack", "off", "on", self.selection)

    def test_missing_scheduled_kd_is_not_a_successful_control(self):
        self.report["rounds"][0]["clusters"]["medium"]["kd"] = {"performed": False, "reason": "no_eligible_teacher"}
        with self.assertRaisesRegex(ValueError, "scheduled KD"):
            validate_completed_run(self.report, self.manifest, "attack", "off", "on", self.selection)

    def test_initial_state_or_metric_tampering_fails(self):
        self.report["initial_state_sha256"]["small"] = ["changed"]
        with self.assertRaisesRegex(ValueError, "initial_state"):
            validate_completed_run(self.report, self.manifest, "attack", "off", "on", self.selection)


if __name__ == "__main__":
    unittest.main()
