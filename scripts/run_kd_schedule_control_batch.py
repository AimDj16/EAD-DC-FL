"""Run four bounded within-FL KD schedule controls and archive their reports.

Default: EAD on, existing seed42 12-round manifest, benign and label flipping.
Original full-KD runs are reused as references, never rerun or overwritten.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.matched_experiments import load_matched_experiment, file_sha256
from ead_dc_fl.kd_control_protocol import (
    ARCHITECTURES, control_directory, exact_prefix_length, original_directory,
    paired_summary, validate_reference, verify_common_inputs, verify_policy_record,
)
from check_matched_run_inputs import fingerprint


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def verify_completed(report, manifest, policy, arm, reference, hashes):
    if (report.get("status") != "completed"
            or report.get("configuration_id") != "matched_kd_schedule_controls_v1"
            or report.get("kd_policy") != policy or report.get("arm") != arm
            or report.get("script_sha256") != hashes["runner"]
            or report.get("policy_module_sha256") != hashes["policy"]
            or report.get("original_runner_sha256") != hashes["original"]
            or report.get("test_evaluated") is not False
            or report.get("final_protocol_frozen") is not False
            or report.get("first_round_pre_kd_replay_exact") is not True
            or report.get("master_unchanged") is not True
            or report.get("reference_report_unchanged") is not True):
        raise ValueError("Existing KD control is incomplete or different; preserve and inspect it.")
    verify_common_inputs(report, reference)
    if fingerprint(report) != fingerprint(reference):
        raise ValueError("Existing KD control has different matched local inputs.")
    prefix = exact_prefix_length(policy, manifest["rounds"])
    expected = [{"round": n, "exact_records": True, "exact_tensors": True}
                for n in range(1, prefix + 1)]
    if report.get("shared_policy_prefix_checks") != expected:
        raise ValueError("Existing KD control lacks exact shared-policy replay checks.")
    for record in report["rounds"]:
        verify_policy_record(record, policy)


def archive_reports(path, files):
    """Reuse an identical archive; preserve a conflicting one for inspection."""
    names = {p.as_posix(): p for p in files}
    if len(names) != len(files):
        raise ValueError("Archive paths must be unique.")
    if path.exists():
        with tarfile.open(path, "r:gz") as archive:
            members = [m for m in archive.getmembers() if m.isfile()]
            if (len(members) != len(names) or {m.name for m in members} != set(names)
                    or any(hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                           != file_sha256(names[m.name]) for m in members)):
                raise FileExistsError("Different existing archive preserved: " + str(path))
        return
    temporary = path.with_suffix(path.suffix + ".partial")
    with tarfile.open(temporary, "w:gz") as archive:
        for name in sorted(names):
            archive.add(names[name], arcname=name, recursive=False)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matched-experiment", type=Path, default=Path(
        "data/experiments/idsiot2024/replication_seed42_rounds12_v1"))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    manifest = read_json(args.matched_experiment / "manifest.json")
    if manifest["rounds"] != 12:
        parser.error("This bounded programme requires the existing 12-round contract.")
    manifest = load_matched_experiment(args.matched_experiment, manifest["seed"],
                                       manifest["rounds"], manifest["training_settings"])
    runner = Path("scripts/run_kd_schedule_control.py")
    policy_module = Path("src/ead_dc_fl/kd_control_protocol.py")
    original_runner = Path("scripts/run_matched_replication.py")
    hashes = {"runner": file_sha256(runner), "policy": file_sha256(policy_module),
              "original": file_sha256(original_runner)}
    policies = ("warm_start_only", "adaptive_only")
    references, jobs = {}, []
    for arm in ("benign", "attack"):
        directory = original_directory(manifest, arm)
        reference = read_json(directory / "report.json")
        validate_reference(reference, manifest, arm, "on", hashes["original"])
        fingerprint(reference)
        references[arm] = (directory, reference)
        for number in range(1, 4):
            for architecture in ARCHITECTURES:
                checkpoint = directory / f"round_{number:02d}" / f"{architecture}_weights.npz"
                if file_sha256(checkpoint) != reference["rounds"][number - 1]["checkpoint_hashes"][architecture]:
                    raise ValueError("Original prefix checkpoint changed: " + str(checkpoint))
        for policy in policies:
            output = control_directory(manifest, policy, arm)
            if output.exists():
                report = read_json(output / "report.json")
                verify_completed(report, manifest, policy, arm, reference, hashes)
                if report["reference_report_sha256"] != file_sha256(directory / "report.json"):
                    raise ValueError("Original reference report changed since this control.")
                for record in report["rounds"]:
                    for architecture in ARCHITECTURES:
                        checkpoint = output / f"round_{record['round']:02d}" / f"{architecture}_weights.npz"
                        if file_sha256(checkpoint) != record["checkpoint_hashes"][architecture]:
                            raise ValueError("Existing control checkpoint changed: " + str(checkpoint))
            jobs.append((policy, arm, output))
    if fingerprint(references["benign"][1]) != fingerprint(references["attack"][1]):
        raise ValueError("Original benign and targeted reference local inputs differ.")
    print("KD CONTROL PREFLIGHT: PASS", flush=True)
    print("Four controls: two KD schedules x benign/targeted; EAD on; FedAvg.", flush=True)
    print("Data, local budgets and participants fixed; KD exposure intentionally differs.", flush=True)
    if args.preflight_only:
        print("No training performed; final test untouched.")
        return
    reports = {}
    for policy, arm, output in jobs:
        reference_dir, reference = references[arm]
        if not output.exists():
            command = [sys.executable, "-u", str(runner), "--matched-experiment",
                       str(args.matched_experiment), "--seed", str(manifest["seed"]),
                       "--rounds", str(manifest["rounds"]), "--mode", "original",
                       "--ead", "on", "--kd", "on", "--aggregation", "fedavg",
                       "--attack", "gaussian" if arm == "benign" else "targeted",
                       "--arm", arm, "--sigma", "0", "--kd-policy", policy,
                       "--reference", str(reference_dir)]
            print("RUN:", " ".join(command), flush=True)
            subprocess.run(command, check=True)
        else:
            print("REUSE COMPLETED:", output, flush=True)
        report = read_json(output / "report.json")
        verify_completed(report, manifest, policy, arm, reference, hashes)
        reports[(policy, arm)] = report
    summary = {
        "status": "completed", "configuration_id": "kd_schedule_batch_v1",
        "matched_experiment_id": manifest["experiment_id"], "seed": manifest["seed"],
        "rounds": manifest["rounds"], "ead_enabled": True,
        "new_fl_runs": 4, "reused_original_references": 2,
        "new_runner_sha256": hashes["runner"], "policy_module_sha256": hashes["policy"],
        "batch_script_sha256": file_sha256(Path(__file__)),
        "test_evaluated": False, "final_protocol_frozen": False,
        "comparisons": {policy: paired_summary(reports[(policy, "benign")],
                                               reports[(policy, "attack")])
                        for policy in policies},
        "original_full_kd": paired_summary(references["benign"][1], references["attack"][1]),
        "interpretation": "One-seed diagnostic; compare each attack with its own policy-matched benign run. KD exposure differs by design. Adaptive-only retains labelled validation for teacher/gate decisions. No final-test evaluation.",
    }
    all_paths = [control_directory(manifest, policy, arm) / "report.json"
                 for policy, arm, _ in jobs]
    all_paths.extend(directory / "report.json" for directory, _ in references.values())
    summary["source_report_sha256"] = {p.as_posix(): file_sha256(p) for p in all_paths}
    summary_path = Path("outputs/controls") / f"kd_schedule_seed{manifest['seed']}_v1_summary.json"
    content = json.dumps(summary, indent=2, allow_nan=False) + "\n"
    if summary_path.exists() and summary_path.read_text() != content:
        raise FileExistsError("Different existing summary preserved: " + str(summary_path))
    summary_path.write_text(content, encoding="utf-8")
    all_paths.extend([summary_path, args.matched_experiment / "manifest.json", runner,
                      policy_module, Path("scripts/run_kd_schedule_control_batch.py"),
                      Path("docs/kd_schedule_controls.md")])
    archive = Path(f"kd_schedule_seed{manifest['seed']}_v1_reports.tar.gz")
    archive_reports(archive, all_paths)
    print("WITHIN-FL KD CONTROL BATCH AND REPORT ARCHIVE: COMPLETE")
    print("Saved:", summary_path)
    print("Archive:", archive)
    print("SHA256:", file_sha256(archive))
    print("Upload the archive for inspection. Test evaluated: NO")


if __name__ == "__main__":
    main()
