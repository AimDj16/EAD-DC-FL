"""Check completed runs share initial states, data, budgets and actual cohorts."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.matched_experiments import canonical_sha256


def fingerprint(report):
    required = ("matched_experiment_id", "initial_state_sha256", "seed", "planned_rounds",
                "training_settings", "execution_environment", "source_sha256",
                "client_manifest_sha256", "master_weights_sha256", "models_and_kd_sha256")
    if report.get("status") != "completed":
        raise ValueError("Run is not completed.")
    if any(key not in report for key in required):
        raise ValueError("Missing matched-run metadata; legacy runs cannot pass this audit.")
    records = report.get("rounds", [])
    if [record["round"] for record in records] != list(range(1, report["planned_rounds"] + 1)):
        raise ValueError("Rounds are incomplete, duplicated or out of order.")
    value = {key: report[key] for key in required}
    value["round_inputs"] = []
    for record in records:
        participants = {name: cluster["client_ids"] for name, cluster in record["clusters"].items()}
        if (participants != record["participation"]
                or canonical_sha256(participants) != record["participation_sha256"]):
            raise ValueError("Participation record is inconsistent.")
        if (set(report["initial_state_sha256"]) != set(participants)
                or any(not hashes for hashes in report["initial_state_sha256"].values())):
            raise ValueError("Initial tensor hashes do not cover the architecture registry.")
        for name, ids in participants.items():
            if set(record["clusters"][name]["local_training_order_sha256"]) != {str(cid) for cid in ids}:
                raise ValueError("Training-order hashes do not cover every participating client.")
        value["round_inputs"].append({
            "participants": participants,
            "training_orders": {name: cluster["local_training_order_sha256"]
                                for name, cluster in record["clusters"].items()},
        })
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    if len(args.reports) < 2:
        parser.error("Supply at least two completed matched report.json paths.")
    values = []
    for path in args.reports:
        values.append(fingerprint(json.loads(path.read_text(encoding="utf-8-sig"))))
    for path, value in zip(args.reports[1:], values[1:]):
        if value != values[0]:
            fields = [key for key in values[0] if value[key] != values[0][key]]
            raise ValueError("Matched inputs differ for " + str(path) + ": " + ", ".join(fields))
    print("MATCHED INITIAL STATES, DATA, BUDGETS AND PARTICIPATION: PASS")
    print("Report count:", len(values))
    print("Experiment ID:", values[0]["matched_experiment_id"])
    print("EAD decisions, attacks, KD decisions and later model states may differ by design.")


if __name__ == "__main__":
    main()
