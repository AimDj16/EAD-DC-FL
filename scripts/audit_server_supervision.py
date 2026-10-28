"""Audit server-data boundaries and optionally train isolated central references.

No client training, attack, test prediction, or existing-output modification.
References quantify central supervision alone, not its causal contribution in FL.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.preprocessing import StandardScaler


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def check_split_boundaries(partitions, feature_group_ids, row_count):
    names = ("client_training", "server_kd", "server_validation", "test")
    if set(partitions) != set(names) or len(feature_group_ids) != row_count:
        raise ValueError("Unexpected partitions or feature-group registry.")
    for name, rows in partitions.items():
        if (rows.ndim != 1 or not len(rows) or not np.issubdtype(rows.dtype, np.integer)
                or np.any(rows < 0) or np.any(rows >= row_count)):
            raise ValueError("Invalid row indices: " + name)
    all_rows = np.concatenate([partitions[name] for name in names])
    if not np.array_equal(np.sort(all_rows), np.arange(row_count)):
        raise ValueError("Partitions do not allocate every row exactly once.")
    overlaps = {}
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            count = len(np.intersect1d(feature_group_ids[partitions[left]],
                                      feature_group_ids[partitions[right]]))
            overlaps[left + "__" + right] = count
            if count:
                raise ValueError("Feature groups cross partition boundaries: " + left + "/" + right)
    return overlaps


def check_training_normalisation(raw_training, normalisation):
    reference = StandardScaler().fit(raw_training)
    for field, actual in (("mean", reference.mean_), ("scale", reference.scale_),
                          ("variance", reference.var_)):
        saved = np.asarray(normalisation[field])
        if saved.shape != actual.shape or not np.allclose(saved, actual, rtol=1e-10, atol=1e-12):
            raise ValueError("Saved normalisation does not match client-training-only fit: " + field)
    if not np.all(np.asarray(normalisation["samples_seen"]) == len(raw_training)):
        raise ValueError("Normalisation sample count differs from client training.")
    return dict(fit_partition="client_training", samples_seen=len(raw_training),
                mean_max_absolute_difference=float(np.max(np.abs(normalisation["mean"] - reference.mean_))),
                scale_max_absolute_difference=float(np.max(np.abs(normalisation["scale"] - reference.scale_))),
                comparison_rtol=1e-10, comparison_atol=1e-12,
                upstream_preprocessing_verified=False)


def metrics_from_predictions(labels, predictions, classes):
    labels, predictions = np.asarray(labels), np.asarray(predictions)
    if labels.ndim != 1 or predictions.shape != labels.shape or not len(labels):
        raise ValueError("Require matching nonempty one-dimensional evaluation arrays.")
    if not np.isin(labels, np.arange(len(classes))).all() or not np.isin(predictions, np.arange(len(classes))).all():
        raise ValueError("Evaluation class IDs are outside the registry.")
    source, target = classes.index("Malware"), classes.index("Normal")
    source_mask, normal_mask = labels == source, labels == target
    if not source_mask.any() or not normal_mask.any():
        raise ValueError("Require Malware and Normal validation support.")
    recalls = recall_score(labels, predictions, labels=np.arange(len(classes)), average=None, zero_division=0)
    hits = int(np.sum(predictions[source_mask] == target))
    return dict(accuracy=float(accuracy_score(labels, predictions)),
                macro_f1=float(f1_score(labels, predictions, labels=np.arange(len(classes)), average="macro", zero_division=0)),
                per_class_recall={name: float(recalls[i]) for i, name in enumerate(classes)},
                confusion_matrix=confusion_matrix(labels, predictions, labels=np.arange(len(classes))).tolist(),
                confusion_matrix_order=classes,
                targeted_hits=hits, targeted_source_rows=int(source_mask.sum()),
                targeted_misclassification_rate=hits / int(source_mask.sum()),
                normal_false_alarm_count=int(np.sum(predictions[normal_mask] != target)),
                normal_rows=int(normal_mask.sum()),
                normal_false_alarm_rate=float(np.mean(predictions[normal_mask] != target)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matched-experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-server-only-controls", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Existing output preserved: " + str(args.output))
    started = time.perf_counter()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from ead_dc_fl.matched_experiments import load_matched_experiment, restore_initial_models, array_sha256
    from check_matched_run_inputs import fingerprint

    manifest = read_json(args.matched_experiment / "manifest.json")
    matched = load_matched_experiment(args.matched_experiment, manifest["seed"],
                                     manifest["rounds"], manifest["training_settings"])
    source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
    partition_dir = Path("data/partitions/idsiot2024/candidate_seed42_groups2")
    client_dir = Path("data/clients/idsiot2024/development_iid_seed42")
    master_dir = Path("outputs/development/master_pretrain_seed42")
    partition = read_json(partition_dir / "manifest.json")
    master_report = read_json(master_dir / "report.json")
    if master_report["training_partition"] != "server_kd":
        raise ValueError("Master training partition is not server_kd.")
    for path, expected in ((source, master_report["source_sha256"]),
                           (partition_dir / "indices.npz", master_report["partition_indices_sha256"]),
                           (client_dir / "normalisation.npz", master_report["normalisation_sha256"]),
                           (master_dir / "master_weights.npz", master_report["weights_sha256"])):
        if sha256(path) != expected:
            raise ValueError("Master input/checkpoint hash mismatch: " + str(path))

    import pandas as pd
    frame = pd.read_csv(source)
    names, classes = partition["feature_names"], partition["classes"]
    if master_report["feature_names"] != names or master_report["classes"] != classes:
        raise ValueError("Master class/feature registry differs.")
    with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
        parts = {name: saved[name].copy() for name in partition["partition_order"]}
        group_ids = saved["row_group_id"].copy()
    # Recompute exact feature groups, rather than trusting the saved registry alone.
    actual_groups = frame.groupby(names, sort=True, dropna=False).ngroup().to_numpy(dtype=np.int64)
    if not np.array_equal(group_ids, actual_groups):
        raise ValueError("Saved feature groups differ from the source data.")
    overlaps = check_split_boundaries(parts, group_ids, len(frame))
    with np.load(client_dir / "normalisation.npz", allow_pickle=False) as saved:
        normalisation = {name: saved[name].copy() for name in saved.files}
    raw_training = frame.iloc[parts["client_training"]][names].to_numpy(dtype=np.float64)
    normalisation_checks = check_training_normalisation(raw_training, normalisation)
    del raw_training
    if master_report["training_rows"] != len(parts["server_kd"]):
        raise ValueError("Master reported training row count differs.")
    if master_report["checkpoint_policy"] != "final_epoch":
        raise ValueError("Unexpected master checkpoint-selection policy.")

    mapping = {name: i for i, name in enumerate(classes)}
    def extract(part):
        selected = frame.iloc[parts[part]]
        raw = selected[names].to_numpy(dtype=np.float64)
        features = ((raw - normalisation["mean"]) / normalisation["scale"]).astype(np.float32)
        encoded = selected[partition["protocol"]["target_column"]].map(mapping)
        if encoded.isna().any() or not np.isfinite(features).all():
            raise ValueError("Invalid server features or labels.")
        return features, encoded.to_numpy(dtype=np.int64)

    server_features, server_labels = extract("server_kd")
    val_features, val_labels = extract("server_validation")
    del frame
    seed = manifest["seed"]
    references = []
    reference_fingerprints = []
    pattern = (f"matched_fedavg_{matched['experiment_id'][:12]}_replication_predict3_gaussian"
               f"_sigma0p0_benign_original_ead_*_kd_*_seed{seed}_rounds{manifest['rounds']}/report.json")
    for path in sorted(Path("outputs/development").glob(pattern)):
        report = read_json(path)
        reference_fingerprints.append(fingerprint(report))
        if report["matched_experiment_id"] != matched["experiment_id"]:
            raise ValueError("Benign reference contract differs.")
        if (report["seed"] != seed or report["planned_rounds"] != manifest["rounds"]
                or report["training_settings"] != manifest["training_settings"]
                or report["initial_state_sha256"] != {
                    n: e["tensor_sha256"] for n, e in manifest["initial_models"].items()}
                or report["master_weights_sha256"] != master_report["weights_sha256"]):
            raise ValueError("Benign reference inputs differ from the registered experiment.")
        references.append(dict(path=str(path), sha256=sha256(path), ead=report["ead_enabled"],
                               kd=report["kd_enabled"], final={n: c["post_kd_validation"]
                               for n, c in report["rounds"][-1]["clusters"].items()}))
    if len(references) != 4 or len({(r["ead"], r["kd"]) for r in references}) != 4:
        raise ValueError("Require all four completed same-seed benign component reports.")
    if not all(value == reference_fingerprints[0] for value in reference_fingerprints):
        raise ValueError("Benign references are not matched to one another.")

    import tensorflow as tf
    from ead_dc_fl.models_and_kd import build_model, copy_weights, distil
    for device in tf.config.list_physical_devices("GPU"):
        tf.config.experimental.set_memory_growth(device, True)
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()
    architectures = ("small", "medium", "deep")
    initial_models = {name: build_model(name, len(names), len(classes)) for name in architectures}
    initial_hashes = restore_initial_models(initial_models, matched, args.matched_experiment)
    initial_weights = {name: copy_weights(model) for name, model in initial_models.items()}
    del initial_models
    master = build_model("master", len(names), len(classes))
    with np.load(master_dir / "master_weights.npz", allow_pickle=False) as saved:
        master.set_weights([saved[key] for key in sorted(saved.files)])
    master_tensor_hashes = [array_sha256(w) for w in master.get_weights()]

    def evaluate(model, label):
        batches = []
        for start in range(0, len(val_features), 256):
            features = val_features[start:start + 256]
            logits = model(features, training=False).numpy()
            if logits.shape != (len(features), len(classes)) or not np.isfinite(logits).all():
                raise FloatingPointError("Invalid validation logits: " + label)
            batches.append(logits.argmax(axis=1))
        predictions = np.concatenate(batches)
        metrics = metrics_from_predictions(val_labels, predictions, classes)
        np.savez_compressed(args.output / (label + "_validation_predictions.npz"), predictions=predictions)
        return metrics

    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.output / "report.json"
    output = dict(status="running", configuration_id="server_supervision_reference_v1",
        seed=seed, script_sha256=sha256(__file__), matched_experiment_id=matched["experiment_id"],
        initial_state_sha256=initial_hashes, master_weights_sha256=master_report["weights_sha256"],
        source_sha256=sha256(source), models_and_kd_sha256=sha256(Path("src/ead_dc_fl/models_and_kd.py")),
        partition_feature_group_overlaps=overlaps, normalisation_checks=normalisation_checks,
        environment=dict(python=platform.python_version(), tensorflow=tf.__version__, numpy=np.__version__,
                         sklearn=importlib.metadata.version("scikit-learn"),
                         gpus=[d.name for d in tf.config.list_physical_devices("GPU")]),
        data_roles=dict(master_pretraining=dict(partition="server_kd", rows=len(server_features), labels_used=True,
                                               epochs=master_report["epochs"],
                                               labelled_training_presentations=master_report["epochs"] * len(server_labels),
                                               checkpoint_policy="final_epoch"),
                        recurring_kd=dict(partition="server_kd", rows=len(server_features), labels_used=False,
                                          loss="KL(teacher||student), temperature3"),
                        validation=dict(partition="server_validation", rows=len(val_features), labels_used=True,
                                        roles=["teacher_selection", "KD_acceptance", "reported_development_metrics"])),
        server_class_counts={name: int(np.sum(server_labels == i)) for i, name in enumerate(classes)},
        validation_class_counts={name: int(np.sum(val_labels == i)) for i, name in enumerate(classes)},
        master_reported_validation=master_report["validation"], benign_references=references,
        controls=[], test_evaluated=False, upstream_preprocessing_verified=False,
        limitations=["Conditional on fixed processed representation and master checkpoint.",
                     "Central references are not attacked and do not establish poisoning robustness.",
                     "Training budgets are reported, not compute-matched to FL.",
                     "Distilled references inherit master pretraining; that original compute is not remeasured here.",
                     "These controls do not isolate master contribution inside interacting FL.",
                     "Validation outcomes are development outcomes, not independent final-test results."])
    output["master_recomputed_validation"] = evaluate(master, "master")
    old, new = master_report["validation"], output["master_recomputed_validation"]
    matches = all(np.isclose(old[k], new[k], rtol=0, atol=1e-12) for k in ("accuracy", "macro_f1"))
    matches = bool(matches and all(np.isclose(old["per_class_recall"][name], new["per_class_recall"][name],
                                             rtol=0, atol=1e-12) for name in classes))
    output["master_saved_validation_metrics_match"] = matches
    report_path.write_text(json.dumps(output, indent=2) + "\n")
    if not matches:
        output["status"] = "reference_mismatch"
        report_path.write_text(json.dumps(output, indent=2) + "\n")
        raise RuntimeError("Master validation metrics differ; audit saved, no student controls trained.")
    print("SERVER BOUNDARIES, TRAINING-ONLY NORMALISATION AND MASTER REPLAY: PASS", flush=True)

    if args.include_server_only_controls:
        for architecture_index, architecture in enumerate(architectures):
            for kind in ("server_supervised_only", "master_distilled_only"):
                tf.keras.utils.set_random_seed(seed + architecture_index)
                student = build_model(architecture, len(names), len(classes))
                student.set_weights([w.copy() for w in initial_weights[architecture]])
                before = evaluate(student, architecture + "_" + kind + "_initial")
                control_started = time.perf_counter()
                if kind == "server_supervised_only":
                    epochs = master_report["epochs"]
                    student.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=master_report["learning_rate"]),
                                    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=["accuracy"])
                    history = student.fit(server_features, server_labels, epochs=epochs,
                                          batch_size=master_report["batch_size"], shuffle=True, verbose=2).history
                    details = dict(epochs=epochs, labelled_training_presentations=epochs * len(server_labels),
                                   history=history, checkpoint_policy="final_epoch")
                else:
                    epochs = 3 * 3
                    losses = [distil(student, master, server_features, epochs=3, batch_size=256,
                                     learning_rate=0.001, temperature=3.0,
                                     seed=seed + 1000 * warm_round + architecture_index)
                              for warm_round in (1, 2, 3)]
                    details = dict(epochs=epochs, labelled_training_presentations=0,
                                   inherited_master_training_labels=len(server_labels),
                                   unlabeled_kd_presentations=epochs * len(server_labels), epoch_losses=losses,
                                   acceptance_policy="unconditional_reference", checkpoint_policy="final_KD_epoch")
                elapsed = time.perf_counter() - control_started
                after = evaluate(student, architecture + "_" + kind)
                checkpoint = args.output / (architecture + "_" + kind + "_weights.npz")
                np.savez_compressed(checkpoint, **{f"tensor_{i:02d}": w for i, w in enumerate(student.get_weights())})
                output["controls"].append(dict(architecture=architecture, condition=kind, initial_validation=before,
                    final_validation=after, training_seconds=elapsed, details=details,
                    weights_sha256=sha256(checkpoint), client_training_performed=False))
                report_path.write_text(json.dumps(output, indent=2) + "\n")
                print(f"{architecture} {kind}: accuracy={after['accuracy']:.4f}, macro-F1={after['macro_f1']:.4f}", flush=True)
                del student
    if master_tensor_hashes != [array_sha256(w) for w in master.get_weights()]:
        raise RuntimeError("Master weights changed during the audit.")
    output.update(status="completed", elapsed_seconds=time.perf_counter() - started,
                  master_unchanged=True, existing_outputs_modified=False)
    report_path.write_text(json.dumps(output, indent=2) + "\n")
    print("SERVER SUPERVISION AUDIT AND REQUESTED REFERENCES: COMPLETE")
    print("Test evaluated: NO")
    print("Saved:", report_path)


if __name__ == "__main__":
    main()
