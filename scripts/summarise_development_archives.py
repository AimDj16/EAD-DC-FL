"""Audit matched report archives and export descriptive development summaries.

Reads JSON directly from tar archives, without extracting their member paths.
Runs, rather than clients/rounds, are the replication unit. No test data are used.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from check_matched_run_inputs import fingerprint
from ead_dc_fl.matched_experiments import canonical_sha256

ARCHITECTURES = ("small", "medium", "deep")
METHODS = ((False, False), (True, False), (False, True), (True, True))
LABELS = ("FedAvg", "EAD + FedAvg", "KD + FedAvg", "EAD + KD + FedAvg")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    reports, manifests = {}, {}
    for path in args.archives:
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith(("/report.json", "/manifest.json")):
                    continue
                value = json.load(archive.extractfile(member))
                if member.name.endswith("/manifest.json"):
                    seed = value["seed"]
                    if seed in manifests:
                        assert manifests[seed] == value
                    manifests[seed] = value
                    continue
                family = "benign" if value["arm"] == "benign" else (
                    "targeted" if value["attack_protocol"]["attack"] == "targeted_label_flipping" else "gaussian")
                key = (value["seed"], family, value["ead_enabled"], value["kd_enabled"])
                assert key not in reports, ("Duplicate condition", key)
                reports[key] = value

    for seed, manifest in manifests.items():
        assert manifest["experiment_id"] == canonical_sha256({
            k: v for k, v in manifest.items() if k != "experiment_id"})
        values = [fingerprint(r) for key, r in reports.items() if key[0] == seed]
        assert all(value == values[0] for value in values)
    for (seed, family, ead, kd), report in reports.items():
        manifest = manifests[seed]
        assert report["script_sha256"] == manifest["input_sha256"]["scripts/run_matched_replication.py"]
        assert report["initial_state_sha256"] == {
            name: entry["tensor_sha256"] for name, entry in manifest["initial_models"].items()}
        assert not report["test_evaluated"] and not report["final_protocol_frozen"]
        expected = {entry["client_id"]: entry["poisoned_rows"]
                    for entry in report["attack_protocol"].get("clients", [])}
        if family == "targeted":
            assert sum(expected.values()) == 1497
            assert report["attack_protocol"]["source_class"] == "Malware"
            assert report["attack_protocol"]["destination_class"] == "Normal"
        for record in report["rounds"]:
            assert record["participation"] == manifest["participation"][str(record["round"])]
            for name, cluster in record["clusters"].items():
                ids = set(cluster["client_ids"])
                rejected = set(cluster["rejected_client_ids"])
                audit = cluster["screening_audit"]
                malicious = set(audit["active_malicious_client_ids"])
                assert set(audit["malicious_rejected"]) == malicious & rejected
                assert set(audit["malicious_accepted"]) == malicious - rejected
                assert set(audit["benign_rejected"]) == rejected - malicious
                counts = {str(cid): manifest["client_sample_counts"][f"client_{cid:02d}"]
                          for cid in ids - rejected}
                assert counts == cluster["accepted_sample_counts"]
                assert len(counts) == cluster["accepted_count"]
                assert all(math.isclose(cluster["fedavg_coefficients"][cid], n / sum(counts.values()),
                                        abs_tol=1e-14) for cid, n in counts.items())
                uploads = cluster["upload_diagnostics"]
                assert {u["client_id"] for u in uploads if u["poisoning_applied"]} == malicious
                if family == "targeted":
                    assert len(malicious) == 3
                    assert all(u["poisoned_label_rows"] == expected.get(u["client_id"], 0) for u in uploads)
                    assert sum(u["poisoned_label_rows"] for u in uploads) == {
                        "small": 500, "medium": 499, "deep": 498}[name]
                if ead:
                    flags = [d["flags"] for d in cluster["final_detection"].values()]
                    assert len(flags) == 3
                    votes = [sum(values) for values in zip(*flags)]
                    assert votes == cluster["vote_counts"]
                    assert rejected == {cid for cid, vote in zip(cluster["client_ids"], votes) if vote == 3}
                    trigger = len(set(cluster["initial_detector_flagged_counts"])) > 1
                    assert cluster["calibration_rerun"] == trigger
                    assert cluster["final_contamination"] == (0.3 if trigger else 0.2)
                pre, post, decision = cluster["pre_kd_validation"], cluster["post_kd_validation"], cluster["kd"]
                for metrics in (pre, post):
                    assert metrics["targeted_source_rows"] == 801
                    assert math.isclose(metrics["targeted_misclassification_rate"], metrics["targeted_hits"] / 801)
                if decision.get("performed"):
                    candidate = decision["candidate_validation"]
                    assert post == (candidate if decision["accepted"] else pre)
                    assert decision["accepted"] == (True if record["round"] <= 3 else candidate["accuracy"] >= pre["accuracy"])
                else:
                    assert pre == post

    runs, screening, trajectories = [], [], []
    for (seed, family, ead, kd), report in sorted(reports.items()):
        baseline = reports[(seed, "benign", ead, kd)]
        totals = dict(TP=0, FN=0, FP=0, TN=0)
        for record in report["rounds"]:
            for cluster in record["clusters"].values():
                audit = cluster["screening_audit"]
                totals["TP"] += len(audit["malicious_rejected"])
                totals["FN"] += len(audit["malicious_accepted"])
                totals["FP"] += len(audit["benign_rejected"])
                totals["TN"] += len(cluster["client_ids"]) - len(audit["active_malicious_client_ids"]) - len(audit["benign_rejected"])
        screening.append(dict(seed=seed, family=family, ead=ead, kd=kd, **totals,
                              elapsed_seconds=report["elapsed_seconds"]))
        for architecture in ARCHITECTURES:
            excess = []
            for record, clean_record in zip(report["rounds"], baseline["rounds"]):
                cluster = record["clusters"][architecture]
                clean = clean_record["clusters"][architecture]
                pre, post = cluster["pre_kd_validation"], cluster["post_kd_validation"]
                delta = 100 * (post["targeted_misclassification_rate"] - clean["post_kd_validation"]["targeted_misclassification_rate"])
                excess.append(delta)
                trajectories.append(dict(seed=seed, family=family, ead=ead, kd=kd,
                    architecture=architecture, round=record["round"], accuracy_pct=100 * post["accuracy"],
                    macro_f1_pct=100 * post["macro_f1"], pre_kd_tmr_pct=100 * pre["targeted_misclassification_rate"],
                    post_kd_tmr_pct=100 * post["targeted_misclassification_rate"], excess_tmr_pp=delta))
            final = report["rounds"][-1]["clusters"][architecture]["post_kd_validation"]
            runs.append(dict(seed=seed, family=family, ead=ead, kd=kd, architecture=architecture,
                accuracy_pct=100 * final["accuracy"], macro_f1_pct=100 * final["macro_f1"],
                final_excess_tmr_pp=excess[-1], mean_excess_tmr_pp=statistics.mean(excess),
                max_excess_tmr_pp=max(excess)))
    means = []
    for family in sorted({key[1] for key in reports}):
        for ead, kd in METHODS:
            for architecture in ARCHITECTURES:
                subset = [r for r in runs if (r["family"], r["ead"], r["kd"], r["architecture"]) ==
                          (family, ead, kd, architecture)]
                row = dict(family=family, ead=ead, kd=kd, architecture=architecture, independent_runs=len(subset))
                for metric in ("accuracy_pct", "macro_f1_pct", "final_excess_tmr_pp", "mean_excess_tmr_pp", "max_excess_tmr_pp"):
                    values = [r[metric] for r in subset]
                    row[metric + "_mean"] = statistics.mean(values)
                    row[metric + "_sample_sd"] = statistics.stdev(values) if len(values) > 1 else None
                means.append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("run_metrics.csv", runs), ("screening_counts.csv", screening),
                       ("round_metrics.csv", trajectories), ("mean_sample_sd.csv", means)):
        write_csv(args.output / name, rows)
    audit = dict(report_count=len(reports), seeds=sorted(manifests),
        experiment_ids={str(seed): m["experiment_id"] for seed, m in manifests.items()},
        archive_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.archives},
        replication_unit="independent training run conditional on fixed data/master/compromised set",
        uncertainty="sample standard deviation across runs, not a confidence interval",
        checkpoint_arrays_independently_reloaded=False, test_evaluated=False, final_protocol_frozen=False)
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    if args.plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 9, "svg.hashsalt": "ead-dc-development-v1"})
        seeds = sorted(manifests)
        colours = ("#333333", "#D55E00", "#009E73", "#0072B2")
        for family, metric, filename, ylabel in (
            ("targeted", "excess_tmr_pp", "targeted_excess_tmr.svg", "Excess Malware-to-Normal error (pp)"),
            ("gaussian", "macro_f1_pct", "gaussian_macro_f1.svg", "Validation macro-F1 (%)"),
        ):
            fig, axes = plt.subplots(len(seeds), 3, figsize=(11, 7), sharex=True, sharey="col", squeeze=False)
            for i, seed in enumerate(seeds):
                for j, architecture in enumerate(ARCHITECTURES):
                    ax = axes[i, j]
                    for (ead, kd), label, colour in zip(METHODS, LABELS, colours):
                        series = [r for r in trajectories if (r["seed"], r["family"], r["ead"], r["kd"], r["architecture"]) ==
                                  (seed, family, ead, kd, architecture)]
                        ax.plot([r["round"] for r in series], [r[metric] for r in series],
                                label=label, color=colour, linewidth=1.6, marker="o", markersize=2.5)
                    ax.set_title(f"{architecture.capitalize()}, seed {seed}")
                    ax.grid(alpha=0.25)
                    if i == len(seeds) - 1:
                        ax.set_xlabel("Round")
                    ax.set_xticks((1, 4, 8, 12))
            handles, labels = axes[0, 0].get_legend_handles_labels()
            fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
            fig.supylabel(ylabel, fontsize=10, x=0.005)
            fig.tight_layout(rect=(0.03, 0.05, 1, 1))
            fig.savefig(args.output / filename, metadata={"Date": None})
            plt.close(fig)
    print(f"REPORT AUDIT AND DESCRIPTIVE EXPORT: PASS; reports={len(reports)}, seeds={sorted(manifests)}")


if __name__ == "__main__":
    main()
