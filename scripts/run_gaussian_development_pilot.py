import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, recall_score
from pyod.models.lof import LOF
from pyod.models.iforest import IForest
from pyod.models.knn import KNN

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.models_and_kd import (
    build_model, copy_weights, distil, commit_or_revert,
)


SEED = 42
LOCAL_EPOCHS = 1
LOCAL_BATCH = 128
LEARNING_RATE = 0.001
KD_EPOCHS = 3
KD_BATCH = 256
KD_SAMPLE_LIMIT = 512

source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
partition_dir = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2"
)
client_dir = Path("data/clients/idsiot2024/development_iid_seed42")
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode", choices=["original", "guarded", "no_warm_start"],
    required=True,
)
parser.add_argument("--ead", choices=["on", "off"], required=True)
parser.add_argument("--kd", choices=["on", "off"], required=True)
parser.add_argument("--arm", choices=["benign", "attack"], required=True)
parser.add_argument("--sigma", type=float, required=True)
args = parser.parse_args()
if not np.isfinite(args.sigma) or args.sigma < 0:
    parser.error("--sigma must be finite and non-negative.")
sigma_tag = str(args.sigma).replace(".", "p")
NOISE_SEED = 242
from ead_dc_fl.attacks import gaussian_weight_poisoning
ROUNDS = 4
WARM_START_ROUNDS = 3
output_dir = Path(
    f"outputs/development/gaussian_sigma{sigma_tag}_{args.arm}_{args.mode}_ead_{args.ead}_kd_{args.kd}_seed42"
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate(model, features, labels, classes):
    predictions = []
    for start in range(0, len(features), 256):
        logits = model(features[start:start + 256], training=False).numpy()
        assert np.isfinite(logits).all()
        predictions.append(logits.argmax(axis=1))
    predictions = np.concatenate(predictions)
    recalls = recall_score(
        labels, predictions, labels=np.arange(len(classes)),
        average=None, zero_division=0,
    )
    source_mask = labels == classes.index("Malware")
    source_count = int(source_mask.sum())
    assert source_count > 0
    target_hits = int(
        (predictions[source_mask] == classes.index("Normal")).sum()
    )
    return {
        "targeted_misclassification_rate": target_hits / source_count,
        "targeted_hits": target_hits,
        "targeted_source_rows": source_count,
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(
            labels, predictions, labels=np.arange(len(classes)),
            average="macro", zero_division=0,
        )),
        "per_class_recall": {
            name: float(recalls[index])
            for index, name in enumerate(classes)
        },
    }


def screen(flat_weights, contamination, seed):
    # Full flattened model weights, screened only within an architecture.
    scaled = StandardScaler().fit_transform(flat_weights)
    assert np.isfinite(scaled).all()

    detectors = {
        "LOF": LOF(n_neighbors=5, contamination=contamination),
        "IForest": IForest(
            contamination=contamination, random_state=seed,
        ),
        "KNN": KNN(n_neighbors=5, contamination=contamination),
    }
    records = {}
    flags = []

    for name, detector in detectors.items():
        detector.fit(scaled)
        scores = np.asarray(detector.decision_scores_)
        labels = np.asarray(detector.labels_, dtype=int)
        assert scores.shape == (10,)
        assert labels.shape == (10,)
        assert np.isfinite(scores).all()
        assert np.isin(labels, [0, 1]).all()

        records[name] = {
            "scores": scores.tolist(),
            "flags": labels.tolist(),
            "threshold": float(detector.threshold_),
        }
        flags.append(labels)

    return np.column_stack(flags), records


if output_dir.exists():
    raise FileExistsError(
        f"{output_dir} already exists. Existing results are preserved."
    )

tf.keras.utils.set_random_seed(SEED)
tf.config.experimental.enable_op_determinism()

partition_manifest = read_json(partition_dir / "manifest.json")
client_manifest = read_json(client_dir / "manifest.json")

assert sha256(source).lower() == partition_manifest["source_sha256"].lower()
assert (
    sha256(partition_dir / "indices.npz").lower()
    == partition_manifest["indices_sha256"].lower()
)
assert (
    sha256(partition_dir / "indices.npz").lower()
    == client_manifest["partition_indices_sha256"].lower()
)
assert (
    sha256(client_dir / "client_indices.npz").lower()
    == client_manifest["client_indices_sha256"].lower()
)
assert (
    sha256(client_dir / "normalisation.npz").lower()
    == client_manifest["normalisation_sha256"].lower()
)

frame = pd.read_csv(source)
classes = partition_manifest["classes"]
feature_names = partition_manifest["feature_names"]
target = partition_manifest["protocol"]["target_column"]
mapping = {name: index for index, name in enumerate(classes)}
encoded = frame[target].map(mapping)
assert encoded.notna().all()
labels = encoded.to_numpy(dtype=np.int64)

with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
    training_rows = saved["client_training"].copy()
    kd_rows = saved["server_kd"].copy()
    validation_rows = saved["server_validation"].copy()

with np.load(client_dir / "client_indices.npz", allow_pickle=False) as saved:
    allocations = {key: saved[key].copy() for key in saved.files}

with np.load(client_dir / "normalisation.npz", allow_pickle=False) as saved:
    mean = saved["mean"].copy()
    scale = saved["scale"].copy()

# Transform only rows needed for training, KD and validation.
used_rows = np.concatenate([training_rows, kd_rows, validation_rows])
assert len(np.unique(used_rows)) == len(used_rows)
row_lookup = np.full(len(frame), -1, dtype=np.int64)
row_lookup[used_rows] = np.arange(len(used_rows))
raw = frame.iloc[used_rows][feature_names].to_numpy(dtype=np.float64)
features = ((raw - mean) / scale).astype(np.float32)
assert np.isfinite(features).all()
del raw, frame

def get_features(rows):
    positions = row_lookup[rows]
    assert (positions >= 0).all()
    return features[positions]

validation_features = get_features(validation_rows)
validation_labels = labels[validation_rows]

rng = np.random.default_rng(SEED)
selected_kd_rows = kd_rows.copy()
kd_features = get_features(selected_kd_rows)

architectures = ("small", "medium", "deep")
models = {
    name: build_model(name, len(feature_names), len(classes))
    for name in architectures
}

master_dir = Path("outputs/development/master_pretrain_seed42")
master_report = read_json(master_dir / "report.json")
master_weights_path = master_dir / "master_weights.npz"
assert sha256(master_weights_path) == master_report["weights_sha256"]
assert sha256(source) == master_report["source_sha256"]
assert (
    sha256(partition_dir / "indices.npz")
    == master_report["partition_indices_sha256"]
)
assert (
    sha256(client_dir / "normalisation.npz")
    == master_report["normalisation_sha256"]
)
assert master_report["classes"] == classes
assert master_report["feature_names"] == feature_names

master = build_model("master", len(feature_names), len(classes))
with np.load(master_weights_path, allow_pickle=False) as saved:
    master.set_weights([saved[key] for key in sorted(saved.files)])


# Reuse compromised identities, with a separate Gaussian attack definition.
selection_path = Path(
    "data/attacks/idsiot2024/malware_to_normal_seed142/protocol.json"
)
selection = read_json(selection_path)
assert sha256(source) == selection["source_sha256"]
assert (
    sha256(client_dir / "manifest.json")
    == selection["client_manifest_sha256"]
)
malicious_ids = set(selection["malicious_client_ids"])
assert len(malicious_ids) == 9
for architecture in architectures:
    members = {
        item["client_id"] for item in client_manifest["clients"]
        if item["architecture"] == architecture
    }
    assert len(members & malicious_ids) == 3

attack_protocol = {
    "attack": "untargeted_additive_gaussian_weight_poisoning",
    "operator": "submitted_local_model_plus_noise",
    "sigma": args.sigma,
    "sigma_units": "absolute_model_weight_units",
    "noise_seed": NOISE_SEED,
    "seed_derivation": "SeedSequence([noise_seed, round, client_id])",
    "malicious_client_ids": sorted(malicious_ids),
    "malicious_fraction": 0.30,
    "attack_rounds": [1, 2, 3, 4],
    "training_labels_poisoned": False,
    "server_data_poisoned": False,
    "final_sigma_selected": False,
}

output_dir.mkdir(parents=True)
run_report = {
    "status": "running",
    "mode": args.mode,
    "arm": args.arm,
    "compromised_selection_sha256": sha256(selection_path),
    "attack_operator_sha256": sha256(Path("src/ead_dc_fl/attacks.py")),
    "attack_protocol": attack_protocol,
    "seed": SEED,
    "planned_rounds": ROUNDS,
    "development_warm_start_rounds": (
        WARM_START_ROUNDS
        if args.kd == "on" and args.mode != "no_warm_start" else 0
    ),
    "ensemble": (
        "three_detectors_strict" if args.ead == "on" else "disabled"
    ),
    "ead_enabled": args.ead == "on",
    "kd_enabled": args.kd == "on",
    "aggregation": "coordinate_wise_median",
    "local_epochs": LOCAL_EPOCHS,
    "local_batch_size": LOCAL_BATCH,
    "learning_rate": LEARNING_RATE,
    "kd_epochs": KD_EPOCHS,
    "kd_batch_size": KD_BATCH,
    "kd_temperature": 3.0,
    "kd_rows_used": selected_kd_rows.tolist(),
    "source_sha256": sha256(source),
    "client_manifest_sha256": sha256(client_dir / "manifest.json"),
    "master_weights_sha256": sha256(master_weights_path),
    "models_and_kd_sha256": sha256(
        Path("src/ead_dc_fl/models_and_kd.py")
    ),
    "script_sha256": sha256(Path(__file__)),
    "test_evaluated": False,
    "final_protocol_frozen": False,
    "preprocessing_provenance_verified": False,
    "rounds": [],
}
for round_number in range(1, ROUNDS + 1):
    warm_phase = (
        args.kd == "on"
        and args.mode != "no_warm_start"
        and round_number <= WARM_START_ROUNDS
    )
    print(
        f"\n=== ROUND {round_number}/{ROUNDS}: "
        f"{'master warm-start' if warm_phase else 'adaptive'} ===",
        flush=True,
    )
    cluster_reports = {}
    eligible_teachers = []

    for cluster_index, architecture in enumerate(architectures):
        server_model = models[architecture]
        initial_weights = copy_weights(server_model)
        members = [
            record for record in client_manifest["clients"]
            if record["architecture"] == architecture
        ]
        assert len(members) == 10

        local_model = build_model(
            architecture, len(feature_names), len(classes)
        )
        uploads = []
        client_ids = []
        losses = []
        upload_diagnostics = []

        print(f"\nTraining {architecture} clients...", flush=True)
        for member in members:
            client_id = member["client_id"]
            tf.keras.utils.set_random_seed(SEED + 1000 * round_number + client_id + 1)
            rows = allocations[f"client_{client_id:02d}"]
            local_model.set_weights(initial_weights)

            # Fresh optimiser for each client's local training.
            local_model.compile(
                optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
                loss=tf.keras.losses.SparseCategoricalCrossentropy(
                    from_logits=True
                ),
            )
            local_labels = labels[rows].copy()
            assert np.array_equal(local_labels, labels[rows])

            history = local_model.fit(
                get_features(rows), local_labels,
                epochs=LOCAL_EPOCHS, batch_size=LOCAL_BATCH,
                shuffle=True, verbose=0,
            )
            loss = float(history.history["loss"][-1])
            assert np.isfinite(loss)
            upload = copy_weights(local_model)
            active_attack = (
                args.arm == "attack"
                and client_id in malicious_ids
                and round_number in attack_protocol["attack_rounds"]
            )
            diagnostics = {
                "client_id": client_id,
                "poisoning_applied": bool(active_attack),
            }
            if active_attack:
                upload, noise_diagnostics = gaussian_weight_poisoning(
                    upload, args.sigma, NOISE_SEED,
                    round_number, client_id,
                )
                diagnostics.update(noise_diagnostics)
            upload_diagnostics.append(diagnostics)
            assert all(np.isfinite(value).all() for value in upload)
            uploads.append(upload)
            client_ids.append(client_id)
            losses.append(loss)
            print(f"  client={client_id:02d}, loss={loss:.4f}", flush=True)

        flat_weights = np.stack([
            np.concatenate([value.ravel() for value in upload])
            for upload in uploads
        ])
        detector_seed = SEED + 1000 * round_number + cluster_index
        if args.ead == "on":
            flags, initial_detection = screen(flat_weights, 0.20, detector_seed)
            counts = flags.sum(axis=0)
            count_range = int(counts.max() - counts.min())
            calibration_rerun = count_range > 0
            contamination = 0.30 if calibration_rerun else 0.20

            if calibration_rerun:
                flags, final_detection = screen(
                    flat_weights, contamination, detector_seed
                )
            else:
                final_detection = initial_detection

            rejected = flags.all(axis=1)
        else:
            flags = np.zeros((len(client_ids), 3), dtype=int)
            counts = np.zeros(3, dtype=int)
            initial_detection = {}
            final_detection = {}
            calibration_rerun = False
            contamination = None
            rejected = np.zeros(len(client_ids), dtype=bool)
        accepted_positions = np.flatnonzero(~rejected)
        fallback = len(accepted_positions) == 0

        if fallback:
            server_model.set_weights(initial_weights)
        else:
            aggregate = [
                np.median(np.stack([
                    uploads[position][tensor_index]
                    for position in accepted_positions
                ]), axis=0)
                for tensor_index in range(len(initial_weights))
            ]
            server_model.set_weights(aggregate)
            eligible_teachers.append(architecture)

        pre_kd = evaluate(
            server_model, validation_features, validation_labels, classes
        )
        cluster_reports[architecture] = {
            "client_ids": client_ids,
            "local_losses": losses,
            "upload_diagnostics": upload_diagnostics,
            "initial_detection": initial_detection,
            "initial_detector_flagged_counts": counts.tolist(),
            "calibration_rerun": bool(calibration_rerun),
            "final_contamination": contamination,
            "final_detection": final_detection,
            "vote_counts": flags.sum(axis=1).tolist(),
            "rejected_client_ids": [
                client_ids[position] for position in np.flatnonzero(rejected)
            ],
            "accepted_count": int(len(accepted_positions)),
            "retained_previous_model": bool(fallback),
            "pre_kd_validation": pre_kd,
        }
        print(
            f"{architecture}: accepted={len(accepted_positions)}/10, "
            f"pre-KD validation accuracy={pre_kd['accuracy']:.4f}",
            flush=True,
        )
        del local_model, uploads, flat_weights

    if warm_phase:
        teacher_name = "master"
        teacher_snapshot = master
        print("\nWarm-start teacher: master", flush=True)
    else:
        # Stable architecture order breaks validation-accuracy ties.
        teacher_name = (
            max(
                eligible_teachers,
                key=lambda name: cluster_reports[name]["pre_kd_validation"]["accuracy"],
            )
            if eligible_teachers else None
        )

        teacher_snapshot = None
        if teacher_name is not None:
            teacher_snapshot = build_model(
                teacher_name, len(feature_names), len(classes)
            )
            teacher_snapshot.set_weights(copy_weights(models[teacher_name]))

        print(f"\nAdaptive teacher: {teacher_name}", flush=True)

    for architecture in architectures:
        model = models[architecture]
        record = cluster_reports[architecture]
        skip_reason = None

        if args.kd == "off":
            skip_reason = "kd_disabled"
        elif record["retained_previous_model"]:
            skip_reason = "no_accepted_uploads"
        elif teacher_name is None:
            skip_reason = "no_eligible_teacher"
        elif architecture == teacher_name:
            skip_reason = "teacher_self_distillation"

        if skip_reason:
            record["kd"] = {"performed": False, "reason": skip_reason}
            record["post_kd_validation"] = record["pre_kd_validation"]
            continue

        pre_kd_weights = copy_weights(model)
        kd_losses = distil(
            model, teacher_snapshot, kd_features,
            epochs=KD_EPOCHS, batch_size=KD_BATCH,
            learning_rate=LEARNING_RATE, temperature=3.0,
            seed=SEED + 1000 * round_number + architectures.index(architecture),
        )
        candidate_metrics = evaluate(
            model, validation_features, validation_labels, classes
        )
        unconditional = warm_phase and args.mode == "original"
        accepted = True if unconditional else commit_or_revert(
            model, pre_kd_weights,
            record["pre_kd_validation"]["accuracy"],
            candidate_metrics["accuracy"],
        )
        record["acceptance_policy"] = (
            "unconditional_master_warm_start" if unconditional
            else "validation_accuracy_guard"
        )
        record["kd"] = {
            "performed": True,
            "epoch_losses": kd_losses,
            "candidate_validation": candidate_metrics,
            "accepted": accepted,
        }
        record["post_kd_validation"] = (
            candidate_metrics if accepted else record["pre_kd_validation"]
        )
        if not unconditional:
            assert (
                record["post_kd_validation"]["accuracy"]
                >= record["pre_kd_validation"]["accuracy"]
            )
        print(
            f"{architecture}: KD accepted={accepted}, "
            f"candidate accuracy={candidate_metrics['accuracy']:.4f}, "
            f"committed accuracy="
            f"{record['post_kd_validation']['accuracy']:.4f}",
            flush=True,
        )


    for architecture, record in cluster_reports.items():
        cohort = set(record["client_ids"])
        compromised = (
            cohort & malicious_ids
            if args.arm == "attack"
            and round_number in attack_protocol["attack_rounds"]
            else set()
        )
        benign = cohort - compromised
        rejected_ids = set(record["rejected_client_ids"])
        record["screening_audit"] = {
            "active_malicious_client_ids": sorted(compromised),
            "malicious_rejected": sorted(rejected_ids & compromised),
            "malicious_accepted": sorted(compromised - rejected_ids),
            "benign_rejected": sorted(rejected_ids & benign),
            "malicious_detection_rate": (
                len(rejected_ids & compromised) / len(compromised)
                if compromised else None
            ),
            "benign_rejection_rate": (
                len(rejected_ids & benign) / len(benign)
                if benign else None
            ),
        }
        metrics = record["post_kd_validation"]
        print(
            f"Round {round_number} {architecture}: "
            f"Malware->Normal TMR="
            f"{metrics['targeted_misclassification_rate']:.4f}, "
            f"malicious accepted={len(compromised - rejected_ids)}, "
            f"benign rejected={len(rejected_ids & benign)}",
            flush=True,
        )

    round_dir = output_dir / f"round_{round_number:02d}"
    round_dir.mkdir()
    checkpoint_hashes = {}
    for architecture, model in models.items():
        checkpoint = round_dir / f"{architecture}_weights.npz"
        np.savez_compressed(
            checkpoint,
            **{
                f"tensor_{index:02d}": value
                for index, value in enumerate(model.get_weights())
            },
        )
        checkpoint_hashes[architecture] = sha256(checkpoint)

    round_report = {
        "round": round_number,
        "phase": "master_warm_start" if warm_phase else "adaptive",
        "teacher": teacher_name,
        "teacher_tie_breaking": list(architectures),
        "clusters": cluster_reports,
        "checkpoint_hashes": checkpoint_hashes,
    }
    (round_dir / "report.json").write_text(
        json.dumps(round_report, indent=2), encoding="utf-8"
    )
    run_report["rounds"].append(round_report)
    (output_dir / "report.json").write_text(
        json.dumps(run_report, indent=2), encoding="utf-8"
    )

    for architecture, record in cluster_reports.items():
        metrics = record["post_kd_validation"]
        print(
            f"Round {round_number} {architecture}: "
            f"accuracy={metrics['accuracy']:.4f}, "
            f"macro-F1={metrics['macro_f1']:.4f}, "
            f"DoS recall={metrics['per_class_recall']['DoS']:.4f}",
            flush=True,
        )

run_report["status"] = "completed"
(output_dir / "report.json").write_text(
    json.dumps(run_report, indent=2), encoding="utf-8"
)
print("\nGAUSSIAN DEVELOPMENT PILOT: COMPLETE")
print(f"Sigma: {args.sigma}")
print("Final sigma selected: NO")
print(f"Mode: {args.mode}")
print("Test evaluated: NO")
print("Final protocol frozen: NO")
print(f"Saved: {output_dir / 'report.json'}")
