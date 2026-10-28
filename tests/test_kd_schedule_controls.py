"""Scientific-boundary and fail-closed checks, without TensorFlow or real data."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from ead_dc_fl.kd_control_protocol import (
    ARCHITECTURES, COMMON_KEYS, PRE_KD_KEYS, exact_prefix_length, paired_summary,
    phase_for_round, validate_reference, verify_common_inputs,
    verify_exact_prefix, verify_first_pre_kd, verify_policy_record,
)
from run_kd_schedule_control_batch import archive_reports


def metrics(accuracy=0.8, tmr=0.1):
    return {"accuracy": accuracy, "macro_f1": 0.7,
            "targeted_misclassification_rate": tmr}


def round_record(number, phase="adaptive", teacher="deep"):
    clusters = {}
    for name in ARCHITECTURES:
        pre, candidate = metrics(), metrics(0.9)
        kd = {"performed": True, "candidate_validation": candidate, "accepted": True}
        post = candidate
        if name == teacher:
            kd = {"performed": False, "reason": "teacher_self_distillation"}
            post = pre
        clusters[name] = {key: [] for key in PRE_KD_KEYS}
        clusters[name].update({"pre_kd_validation": pre, "post_kd_validation": post,
                               "kd": kd, "retained_previous_model": False})
    return {"round": number, "phase": phase, "teacher": teacher,
            "teacher_tie_breaking": list(ARCHITECTURES), "participation": {},
            "participation_sha256": "fixture", "clusters": clusters}


class PolicyChecks(unittest.TestCase):
    def test_master_never_used_by_adaptive_only(self):
        for number in range(1, 13):
            self.assertEqual(phase_for_round("adaptive_only", number), "adaptive")
        record = round_record(1, "adaptive", "master")
        with self.assertRaisesRegex(ValueError, "must not use the master"):
            verify_policy_record(record, "adaptive_only")

    def test_shared_prefix_limits_and_invalid_policy(self):
        self.assertEqual(exact_prefix_length("warm_start_only", 12), 3)
        self.assertEqual(exact_prefix_length("adaptive_only", 12), 0)
        self.assertEqual(exact_prefix_length("full_replay", 12), 12)
        with self.assertRaises(ValueError):
            phase_for_round("unregistered", 1)

    def test_warm_start_only_stops_every_architecture(self):
        record = round_record(4, "no_kd", None)
        for cluster in record["clusters"].values():
            cluster["kd"] = {"performed": False, "reason": "kd_schedule_disabled"}
            cluster["post_kd_validation"] = cluster["pre_kd_validation"]
        verify_policy_record(record, "warm_start_only")
        record["clusters"]["small"]["kd"] = {"performed": True}
        with self.assertRaisesRegex(ValueError, "not disabled"):
            verify_policy_record(record, "warm_start_only")

    def test_original_unconditional_warm_start_is_preserved(self):
        record = round_record(1, "master_warm_start", "master")
        for cluster in record["clusters"].values():
            cluster["kd"]["candidate_validation"] = metrics(0.1)
            cluster["post_kd_validation"] = cluster["kd"]["candidate_validation"]
        verify_policy_record(record, "warm_start_only")

    def test_accuracy_guard_rejection_and_equality(self):
        record = round_record(4)
        verify_policy_record(record, "adaptive_only")
        cluster = record["clusters"]["small"]
        cluster["kd"]["candidate_validation"] = metrics(0.7)
        cluster["kd"]["accepted"] = False
        cluster["post_kd_validation"] = cluster["pre_kd_validation"]
        verify_policy_record(record, "adaptive_only")
        cluster["kd"]["candidate_validation"] = metrics(0.8)
        with self.assertRaisesRegex(ValueError, "acceptance"):
            verify_policy_record(record, "adaptive_only")
        cluster["kd"]["accepted"] = True
        cluster["post_kd_validation"] = cluster["kd"]["candidate_validation"]
        verify_policy_record(record, "adaptive_only")

    def test_no_upload_fallback_does_not_distil(self):
        record = round_record(1)
        cluster = record["clusters"]["small"]
        cluster["retained_previous_model"] = True
        with self.assertRaisesRegex(ValueError, "fallback"):
            verify_policy_record(record, "adaptive_only")
        cluster["kd"] = {"performed": False, "reason": "no_accepted_uploads"}
        cluster["post_kd_validation"] = cluster["pre_kd_validation"]
        verify_policy_record(record, "adaptive_only")


class CounterfactualChecks(unittest.TestCase):
    def test_different_post_kd_is_allowed_but_changed_pre_kd_fails(self):
        reference = round_record(1, "master_warm_start", "master")
        current = round_record(1)
        current["clusters"]["small"]["post_kd_validation"] = metrics(0.95)
        verify_first_pre_kd(current, reference)
        current["clusters"]["small"]["pre_kd_validation"] = metrics(0.2)
        with self.assertRaisesRegex(ValueError, "pre-KD replay differs"):
            verify_first_pre_kd(current, reference)

    def test_prefix_does_not_compare_elapsed_time_but_does_compare_teacher(self):
        reference = round_record(1, "master_warm_start", "master")
        current = copy.deepcopy(reference)
        reference["round_seconds"], current["round_seconds"] = 1.0, 2.0
        verify_exact_prefix(current, reference)
        current["teacher"] = "deep"
        with self.assertRaises(ValueError):
            verify_exact_prefix(current, reference)

    def test_common_input_changes_fail_but_policy_difference_is_allowed(self):
        reference = {key: "fixture" for key in COMMON_KEYS}
        reference.update({"seed": 42, "kd_policy": "full_replay"})
        current = copy.deepcopy(reference)
        current["kd_policy"] = "adaptive_only"
        verify_common_inputs(current, reference)
        current["seed"] = 2026
        with self.assertRaisesRegex(ValueError, "seed"):
            verify_common_inputs(current, reference)

    def test_summary_uses_own_policy_benign_not_original_benign(self):
        benign = {"status": "completed", "arm": "benign", "seed": 42,
                  "kd_policy": "adaptive_only", "planned_rounds": 1,
                  "rounds": [round_record(1)]}
        attack = copy.deepcopy(benign)
        attack["arm"] = "attack"
        for cluster in benign["rounds"][0]["clusters"].values():
            cluster["post_kd_validation"] = metrics(tmr=0.2)
        for cluster in attack["rounds"][0]["clusters"].values():
            cluster["post_kd_validation"] = metrics(tmr=0.3)
        summary = paired_summary(benign, attack)
        self.assertAlmostEqual(summary[0]["peak_positive_excess_tmr_pp"], 10)
        benign["kd_policy"] = "warm_start_only"
        with self.assertRaisesRegex(ValueError, "different KD policies"):
            paired_summary(benign, attack)

    def test_wrong_reference_and_truncated_rounds_fail(self):
        manifest = {"experiment_id": "id", "seed": 42, "rounds": 1,
                    "training_settings": {}}
        report = {"status": "completed", "configuration_id": "matched_replication_predict3_v1",
                  "matched_experiment_id": "id", "seed": 42, "planned_rounds": 1,
                  "training_settings": {}, "mode": "original", "arm": "attack",
                  "ead_enabled": True, "kd_enabled": True,
                  "aggregation": "sample_weighted_fedavg", "script_sha256": "source",
                  "test_evaluated": False, "final_protocol_frozen": False,
                  "attack_protocol": {"attack": "targeted_label_flipping",
                                      "source_class": "Malware", "destination_class": "Normal"},
                  "rounds": [{"round": 1}]}
        validate_reference(report, manifest, "attack", "on", "source")
        report["rounds"] = []
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validate_reference(report, manifest, "attack", "on", "source")
        report["script_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "script_sha256"):
            validate_reference(report, manifest, "attack", "on", "source")

    def test_existing_archive_is_reused_or_preserved_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text('{"status":"completed"}')
            archive = root / "reports.tar.gz"
            # Batch uses relative project paths, as in a portable report bundle.
            import os
            previous = Path.cwd()
            try:
                os.chdir(root)
                archive_reports(Path("reports.tar.gz"), [Path("report.json")])
                first = archive.read_bytes()
                archive_reports(Path("reports.tar.gz"), [Path("report.json")])
                self.assertEqual(first, archive.read_bytes())
                report.write_text("changed")
                with self.assertRaises(FileExistsError):
                    archive_reports(Path("reports.tar.gz"), [Path("report.json")])
                self.assertEqual(first, archive.read_bytes())
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
