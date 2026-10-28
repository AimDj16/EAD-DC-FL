"""Prepare, verify IID fidelity, run 24 label-skew conditions and archive reports."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.matched_experiments import file_sha256, load_matched_experiment
from ead_dc_fl.label_skew import (
    ARCHITECTURES, TRAINING_SETTINGS, iid_reference_directory, run_directory,
    validate_completed_run, verify_labelskew_contract,
    archive_reports,
)
from prepare_labelskew_development import ALLOCATION_DIR, SEEDS, experiment_dir
from check_matched_run_inputs import fingerprint


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def check_checkpoints(directory, report):
    for record in report["rounds"]:
        for name in ARCHITECTURES:
            path = directory / f"round_{record['round']:02d}" / f"{name}_weights.npz"
            if file_sha256(path) != record["checkpoint_hashes"][name]:
                raise ValueError("Checkpoint changed: " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="No TensorFlow replay or training.")
    args = parser.parse_args()
    subprocess.run([sys.executable, "scripts/prepare_labelskew_development.py"], check=True)
    manifests = {seed: verify_labelskew_contract(experiment_dir(seed), seed, 12) for seed in SEEDS}
    selection = read_json(Path(next(iter(manifests.values()))["attack_protocol"]))
    runner = Path("scripts/run_labelskew_development.py")
    runner_hash = file_sha256(runner)
    originals, jobs = {}, []
    for seed in SEEDS:
        manifest = manifests[seed]
        base_directory = Path(manifest["base_iid_experiment_manifest"]).parent
        base = load_matched_experiment(base_directory, seed, 12, TRAINING_SETTINGS)
        reference_fingerprint = None
        for arm in ("benign", "attack"):
            for ead, kd in (("off", "off"), ("on", "off"), ("off", "on"), ("on", "on")):
                reference_dir = iid_reference_directory(base, arm, ead, kd)
                reference = read_json(reference_dir / "report.json")
                if (reference.get("status") != "completed" or reference["matched_experiment_id"] != base["experiment_id"]
                        or reference["script_sha256"] != file_sha256(Path("scripts/run_matched_replication.py"))
                        or reference["ead_enabled"] != (ead == "on") or reference["kd_enabled"] != (kd == "on")
                        or reference["arm"] != arm or reference["mode"] != "original"):
                    raise ValueError("Original IID comparison reference differs: " + str(reference_dir))
                value = fingerprint(reference)
                if reference_fingerprint is None:
                    reference_fingerprint = value
                elif value != reference_fingerprint:
                    raise ValueError("Original IID references do not match each other.")
                originals[seed, arm, ead, kd] = (reference_dir, reference)
                output = run_directory(manifest, arm, ead, kd)
                if output.exists():
                    report = read_json(output / "report.json")
                    validate_completed_run(report, manifest, arm, ead, kd, selection)
                    check_checkpoints(output, report)
                    if report["base_iid_reference_report_sha256"] != file_sha256(reference_dir / "report.json"):
                        raise ValueError("IID comparison reference changed after training.")
                jobs.append((seed, arm, ead, kd, output))
    replay_output = Path("outputs/checks/labelskew_runner_iid_replay_seed42_v1")
    reference_dir, reference = originals[42, "benign", "on", "on"]
    for number in range(1, 5):
        for name in ARCHITECTURES:
            checkpoint = reference_dir / f"round_{number:02d}" / f"{name}_weights.npz"
            if file_sha256(checkpoint) != reference["rounds"][number-1]["checkpoint_hashes"][name]:
                raise ValueError("Original IID fidelity checkpoint changed.")
    print("LABEL-SKEW AND 24 ORIGINAL IID REFERENCES: PREFLIGHT PASS", flush=True)
    print("24 new development runs; same architecture pools and client capacities; fixed attacker IDs.", flush=True)
    if args.prepare_only:
        print("No training/replay performed. Inspect:", ALLOCATION_DIR / "preparation_report.json")
        return
    if not replay_output.exists():
        subprocess.run([
            sys.executable, "-u", str(runner), "--matched-experiment",
            "data/experiments/idsiot2024/replication_seed42_rounds12_v1",
            "--seed", "42", "--rounds", "12", "--mode", "original", "--ead", "on", "--kd", "on",
            "--aggregation", "fedavg", "--arm", "benign", "--attack", "gaussian", "--sigma", "0",
            "--data-regime", "iid-replay", "--iid-reference", str(reference_dir),
        ], check=True)
    replay = read_json(replay_output / "report.json")
    checks = [{"round": n, "original_records_exact": True, "checkpoint_tensors_exact": True} for n in range(1, 5)]
    if (replay.get("status") != "iid_replay_completed" or replay.get("scientific_run_count") != 0
            or replay["script_sha256"] != runner_hash or replay["iid_replay_checks"] != checks
            or replay["label_skew_module_sha256"] != file_sha256(Path("src/ead_dc_fl/label_skew.py"))
            or replay["iid_reference_report_sha256"] != file_sha256(reference_dir / "report.json")):
        raise ValueError("IID fidelity replay is incomplete or different; preserve and inspect.")
    check_checkpoints(replay_output, replay)
    print("IID RUNNER FIDELITY: FOUR ROUNDS VERIFIED", flush=True)
    reports, files = {}, []
    for seed, arm, ead, kd, output in jobs:
        manifest = manifests[seed]
        if not output.exists():
            command = [sys.executable, "-u", str(runner), "--matched-experiment", str(experiment_dir(seed)),
                       "--seed", str(seed), "--rounds", "12", "--mode", "original", "--ead", ead, "--kd", kd,
                       "--aggregation", "fedavg", "--arm", arm, "--attack", "gaussian" if arm == "benign" else "targeted",
                       "--sigma", "0", "--data-regime", "labelskew"]
            print("RUN:", " ".join(command), flush=True)
            subprocess.run(command, check=True)
        else:
            print("REUSE COMPLETED:", output, flush=True)
        report = read_json(output / "report.json")
        validate_completed_run(report, manifest, arm, ead, kd, selection)
        reference_dir, original = originals[seed, arm, ead, kd]
        if report["base_iid_reference_report_sha256"] != file_sha256(reference_dir / "report.json"):
            raise ValueError("Original comparison reference changed during the batch.")
        reports[seed, arm, ead, kd] = report
        files.extend([output / "report.json", reference_dir / "report.json"])
    rows, counts = [], []
    for seed in SEEDS:
        values = [fingerprint(r) for key, r in reports.items() if key[0] == seed]
        if any(v != values[0] for v in values[1:]):
            raise ValueError("Non-IID method/arm inputs do not match within seed.")
    for (seed, arm, ead, kd), report in reports.items():
        benign = reports[seed, "benign", ead, kd]
        original = originals[seed, arm, ead, kd][1]
        totals = dict(designated_TP=0, designated_FN=0, benign_FP=0,
                      effective_poison_TP=0, effective_poison_FN=0)
        for record in report["rounds"]:
            for cluster in record["clusters"].values():
                audit = cluster["screening_audit"]
                effect = cluster["effective_poisoning_screening_audit"]
                totals["designated_TP"] += len(audit["malicious_rejected"])
                totals["designated_FN"] += len(audit["malicious_accepted"])
                totals["benign_FP"] += len(audit["benign_rejected"])
                totals["effective_poison_TP"] += len(effect["effective_poisoned_rejected"])
                totals["effective_poison_FN"] += len(effect["effective_poisoned_accepted"])
        counts.append(dict(seed=seed, arm=arm, ead=ead, kd=kd, **totals))
        for name in ARCHITECTURES:
            final = report["rounds"][-1]["clusters"][name]["post_kd_validation"]
            iid_final = original["rounds"][-1]["clusters"][name]["post_kd_validation"]
            excess = [100*(a["clusters"][name]["post_kd_validation"]["targeted_misclassification_rate"]
                           - b["clusters"][name]["post_kd_validation"]["targeted_misclassification_rate"])
                      for a, b in zip(report["rounds"], benign["rounds"])]
            rows.append(dict(seed=seed, arm=arm, ead=ead, kd=kd, architecture=name,
                labelskew_final_accuracy=final["accuracy"], labelskew_final_macro_f1=final["macro_f1"],
                iid_final_macro_f1=iid_final["macro_f1"], labelskew_minus_iid_macro_f1_pp=100*(final["macro_f1"]-iid_final["macro_f1"]),
                normal_false_alarm_rate=final["normal_false_alarm_rate"],
                peak_positive_excess_tmr_pp=max(0, *excess), excess_tmr_pp_by_round=excess))
    summary = {
        "status": "completed", "configuration_id": "labelskew_batch_v1", "new_fl_runs": 24,
        "new_diagnostic_replays": 1, "reused_iid_comparison_reports": 24,
        "allocation_version": next(iter(manifests.values()))["allocation_version"],
        "seeds": list(SEEDS), "experiment_ids": {str(s): m["experiment_id"] for s, m in manifests.items()},
        "runner_sha256": runner_hash, "batch_script_sha256": file_sha256(Path(__file__)),
        "replication_unit": "training run conditional on one fixed allocation/master/compromised set",
        "poison_opportunity_note": "IID/non-IID attack opportunities can differ; no pure fixed-dose heterogeneity interpretation",
        "poison_rows_per_targeted_round": sum(c["poisoned_rows"] for c in selection["clients"]),
        "screening": counts, "comparisons": rows,
        "elapsed_training_seconds": sum(r["elapsed_seconds"] for r in reports.values()),
        "test_evaluated": False, "final_protocol_frozen": False, "preprocessing_provenance_verified": False,
        "source_report_sha256": {p.as_posix(): file_sha256(p) for p in files},
    }
    output = Path("outputs/analysis/labelskew_a0p5_alloc42_three_seed_v1")
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "summary.json"
    text = json.dumps(summary, indent=2, allow_nan=False) + "\n"
    if summary_path.exists() and summary_path.read_text() != text:
        raise FileExistsError("Different existing summary preserved: " + str(summary_path))
    summary_path.write_text(text)
    files.extend([summary_path, ALLOCATION_DIR / "manifest.json", ALLOCATION_DIR / "preparation_report.json",
                  ALLOCATION_DIR / "experiment_index.json", Path(next(iter(manifests.values()))["attack_protocol"]),
                  replay_output / "report.json", runner, Path("scripts/prepare_labelskew_development.py"),
                  Path("scripts/run_labelskew_batch.py"), Path("src/ead_dc_fl/label_skew.py"),
                  Path("docs/labelskew_development_protocol.md")])
    files.extend(experiment_dir(seed) / "manifest.json" for seed in SEEDS)
    archive = Path("labelskew_a0p5_alloc42_three_seed_reports_v1.tar.gz")
    archive_reports(archive, files)
    print("MATCHED LABEL-SKEW BATCH AND REPORT ARCHIVE: COMPLETE")
    print("24 new FL runs; original results unchanged. Final test evaluated: NO")
    print("Archive:", archive)
    print("SHA256:", file_sha256(archive))


if __name__ == "__main__":
    main()
