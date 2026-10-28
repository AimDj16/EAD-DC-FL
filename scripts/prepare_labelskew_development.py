"""Prepare one fixed label-skew allocation and three contracts, without training."""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.matched_experiments import canonical_sha256, file_sha256, load_matched_experiment
from ead_dc_fl.label_skew import (
    ALLOCATION_VERSION, ARCHITECTURES, TRAINING_SETTINGS, make_allocation,
    poison_opportunities, verify_labelskew_contract,
)


ALLOCATION_DIR = Path("data/clients/idsiot2024/development_labelskew_a0p5_alloc42_v1")
SEEDS = (42, 2026, 31415)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def experiment_dir(seed):
    return Path(f"data/experiments/idsiot2024/labelskew_a0p5_alloc42_seed{seed}_rounds12_v1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    base_directories = {seed: Path(f"data/experiments/idsiot2024/replication_seed{seed}_rounds12_v1") for seed in SEEDS}
    bases = {seed: load_matched_experiment(directory, seed, 12, TRAINING_SETTINGS)
             for seed, directory in base_directories.items()}
    if ALLOCATION_DIR.exists():
        if not (ALLOCATION_DIR / "preparation_report.json").is_file():
            raise FileExistsError("Incomplete existing preparation preserved: " + str(ALLOCATION_DIR))
        report = read_json(ALLOCATION_DIR / "preparation_report.json")
        if report.get("status") != "ready_for_training" or not (ALLOCATION_DIR / "experiment_index.json").is_file():
            raise ValueError("Existing preparation is incomplete; preserve and inspect: " + str(ALLOCATION_DIR))
        index = read_json(ALLOCATION_DIR / "experiment_index.json")
        for seed in SEEDS:
            manifest = verify_labelskew_contract(experiment_dir(seed), seed, 12)
            if (manifest["base_iid_experiment_id"] != bases[seed]["experiment_id"]
                    or index["experiment_ids"][str(seed)] != manifest["experiment_id"]):
                raise ValueError("Existing label-skew contract differs.")
        print("LABEL-SKEW PREPARATION: REUSE VERIFIED")
        print("No training performed; test not evaluated.")
        return
    if any(experiment_dir(seed).exists() for seed in SEEDS):
        raise FileExistsError("Label-skew experiment directory already exists without its allocation; inspect before continuing.")
    source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
    partition_dir = Path("data/partitions/idsiot2024/candidate_seed42_groups2")
    iid_dir = Path("data/clients/idsiot2024/development_iid_seed42")
    selection_dir = Path("data/attacks/idsiot2024/malware_to_normal_seed142")
    original_manifest = read_json(iid_dir / "manifest.json")
    partition = read_json(partition_dir / "manifest.json")
    selection = read_json(selection_dir / "protocol.json")
    for base in bases.values():
        if base["client_manifest"] != (iid_dir / "manifest.json").as_posix():
            raise ValueError("Expected the registered common IID allocation.")
    classes = original_manifest["classes"]
    members = {name: [int(c["client_id"]) for c in original_manifest["clients"] if c["architecture"] == name]
               for name in ARCHITECTURES}
    if any(len(ids) != 10 for ids in members.values()):
        raise ValueError("Require ten clients per architecture.")
    with np.load(iid_dir / "client_indices.npz", allow_pickle=False) as saved:
        original = {key: saved[key].copy() for key in saved.files}
    with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
        training_rows = saved["client_training"].copy()
        if not np.array_equal(np.sort(np.concatenate(list(original.values()))), np.sort(training_rows)):
            raise ValueError("Original clients do not cover the registered training pool.")
    # Allocation uses client-training labels only, no validation/test labels or metrics.
    target = partition["protocol"]["target_column"]
    frame = pd.read_csv(source, usecols=[target])
    encoded = frame.iloc[training_rows][target].map({name: j for j, name in enumerate(classes)})
    if encoded.isna().any():
        raise ValueError("Unknown training class.")
    labels = np.full(len(frame), -1, dtype=np.int64)
    labels[training_rows] = encoded.to_numpy(dtype=np.int64)
    changed, distributions = make_allocation(original, labels, members, len(classes), alpha=0.5, seed=42)
    malicious = selection["malicious_client_ids"]
    poison = poison_opportunities(changed, labels, malicious, classes.index("Malware"))
    if len(malicious) != 9 or any(len(set(ids) & set(malicious)) != 3 for ids in members.values()):
        raise ValueError("Expected the same nine designated compromised identities.")
    opportunity = {key: len(rows) for key, rows in poison.items()}
    quality = all(d["labelskew"]["mean_total_variation"] >= 0.10
                  and d["labelskew"]["mean_total_variation"] > d["iid"]["mean_total_variation"] + 0.05
                  for d in distributions.values())
    report = {
        "status": "prepared" if quality and sum(opportunity.values()) > 0 else "allocation_quality_failed",
        "allocation_version": ALLOCATION_VERSION, "dirichlet_alpha": 0.5, "allocation_seed": 42,
        "quality_rule": "each group mean TV >=0.10 and > IID mean TV+0.05; positive total compromised Malware opportunity; no redraw",
        "quality_passed": quality, "distributions": distributions,
        "poison_rows_by_designated_client": opportunity,
        "total_poison_rows_per_targeted_round": sum(opportunity.values()),
        "zero_opportunity_compromised_clients": [int(key.split('_')[1]) for key, count in opportunity.items() if count == 0],
        "training_performed": False, "test_evaluated": False, "final_protocol_frozen": False,
        "preprocessing_provenance_verified": False,
    }
    ALLOCATION_DIR.mkdir(parents=True, exist_ok=False)
    (ALLOCATION_DIR / "preparation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["status"] != "prepared":
        raise ValueError("Predeclared allocation quality/opportunity check failed. Saved diagnostics; no automatic redraw and no training.")
    np.savez_compressed(ALLOCATION_DIR / "client_indices.npz", **changed)
    shutil.copyfile(iid_dir / "normalisation.npz", ALLOCATION_DIR / "normalisation.npz")
    client_manifest = copy.deepcopy(original_manifest)
    client_manifest.update({
        "status": "labelskew_development_not_frozen", "allocation": ALLOCATION_VERSION,
        "dirichlet_alpha": 0.5, "allocation_seed": 42,
        "base_iid_client_manifest": (iid_dir / "manifest.json").as_posix(),
        "base_iid_client_manifest_sha256": file_sha256(iid_dir / "manifest.json"),
        "client_indices_sha256": file_sha256(ALLOCATION_DIR / "client_indices.npz"),
        "normalisation_sha256": file_sha256(ALLOCATION_DIR / "normalisation.npz"),
        "source_sha256": file_sha256(source),
        "partition_indices_sha256": file_sha256(partition_dir / "indices.npz"),
        "classes": classes, "feature_names": original_manifest["feature_names"],
        "clients": [{**item, "rows": len(changed[f"client_{item['client_id']:02d}"]),
                      "class_counts": {name: int(np.sum(labels[changed[f"client_{item['client_id']:02d}"]] == j))
                                       for j, name in enumerate(classes)}}
                    for item in original_manifest["clients"]],
        "checks": {**original_manifest.get("checks", {}),
                   "all_classes_present_in_every_client": all(
                       np.all(np.bincount(labels[rows], minlength=len(classes)) > 0) for rows in changed.values()),
                   "client_sample_counts_equal_to_iid": True,
                   "architecture_training_pools_equal_to_iid": True},
    })
    (ALLOCATION_DIR / "manifest.json").write_text(json.dumps(client_manifest, indent=2) + "\n")
    attack_dir = ALLOCATION_DIR / "targeted_attack"
    attack_dir.mkdir()
    np.savez_compressed(attack_dir / "poison_rows.npz", **poison)
    attack_protocol = copy.deepcopy(selection)
    attack_protocol.update({
        "status": "labelskew_development_not_frozen",
        "client_manifest_sha256": file_sha256(ALLOCATION_DIR / "manifest.json"),
        "poison_rows_sha256": file_sha256(attack_dir / "poison_rows.npz"),
        "base_selection_protocol_sha256": file_sha256(selection_dir / "protocol.json"),
        "clients": [{"client_id": int(key.split('_')[1]),
                     "architecture": next(name for name, ids in members.items() if int(key.split('_')[1]) in ids),
                     "poisoned_rows": len(rows)} for key, rows in poison.items()],
        "source_class_opportunity_changes_with_allocation": True,
        "designated_clients_may_have_zero_source_rows": True,
    })
    (attack_dir / "protocol.json").write_text(json.dumps(attack_protocol, indent=2) + "\n")
    report["allocation_file_sha256"] = {p.as_posix(): file_sha256(p) for p in (
        ALLOCATION_DIR / "manifest.json", ALLOCATION_DIR / "client_indices.npz",
        ALLOCATION_DIR / "normalisation.npz", attack_dir / "protocol.json", attack_dir / "poison_rows.npz")}
    # First store immutable allocation diagnostics; experiment IDs are stored separately.
    report["status"] = "ready_for_training"
    (ALLOCATION_DIR / "preparation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    experiment_ids = {}
    extra_sources = [Path("src/ead_dc_fl/label_skew.py"), Path(__file__),
                     Path("scripts/run_labelskew_development.py"), Path("scripts/run_labelskew_batch.py"),
                     Path("scripts/check_matched_run_inputs.py"), Path("docs/labelskew_development_protocol.md")]
    for seed, base in bases.items():
        directory = experiment_dir(seed)
        directory.mkdir(parents=True, exist_ok=False)
        for entry in base["initial_models"].values():
            shutil.copyfile(base_directories[seed] / entry["file"], directory / entry["file"])
        manifest = copy.deepcopy(base)
        manifest.pop("experiment_id")
        manifest.update({
            "data_regime": "labelskew", "allocation_version": ALLOCATION_VERSION,
            "allocation_seed": 42, "dirichlet_alpha": 0.5,
            "client_manifest": (ALLOCATION_DIR / "manifest.json").as_posix(),
            "attack_protocol": (attack_dir / "protocol.json").as_posix(),
            "base_iid_experiment_manifest": (base_directories[seed] / "manifest.json").as_posix(),
            "base_iid_experiment_id": base["experiment_id"],
            "base_initial_models": copy.deepcopy(base["initial_models"]),
            "base_client_sample_counts": copy.deepcopy(base["client_sample_counts"]),
            "replication_scope": "training_and_detector_randomness_conditional_on_fixed_labelskew_allocation_master_and_compromised_set",
        })
        manifest["input_sha256"].update(report["allocation_file_sha256"])
        manifest["input_sha256"][(ALLOCATION_DIR / "preparation_report.json").as_posix()] = file_sha256(ALLOCATION_DIR / "preparation_report.json")
        manifest["input_sha256"].update({p.as_posix(): file_sha256(p) for p in extra_sources})
        manifest["input_sha256"][(base_directories[seed] / "manifest.json").as_posix()] = file_sha256(base_directories[seed] / "manifest.json")
        manifest["experiment_id"] = canonical_sha256(manifest)
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        verify_labelskew_contract(directory, seed, 12)
        experiment_ids[str(seed)] = manifest["experiment_id"]
    (ALLOCATION_DIR / "experiment_index.json").write_text(json.dumps({"experiment_ids": experiment_ids}, indent=2) + "\n")
    print("LABEL-SKEW INPUTS AND THREE MATCHED CONTRACTS: CREATED")
    for name, d in distributions.items():
        print(f"{name}: mean TV IID={d['iid']['mean_total_variation']:.4f}, labelskew={d['labelskew']['mean_total_variation']:.4f}")
    print("Poison rows per targeted round:", sum(opportunity.values()), "; by client:", opportunity)
    print("Source-class opportunity differs by design; no labels changed during preparation.")
    print("No training performed; final test untouched. Saved:", ALLOCATION_DIR / "preparation_report.json")


if __name__ == "__main__":
    main()
