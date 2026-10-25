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
output_dir = Path("outputs/checks/benign_master_warmstart_seed42")


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
    return {
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

    print(f"\nTraining {architecture} clients...", flush=True)
    for member in members:
        client_id = member["client_id"]
        tf.keras.utils.set_random_seed(SEED + client_id + 1)
        rows = allocations[f"client_{client_id:02d}"]
        local_model.set_weights(initial_weights)

        # Fresh optimiser for each client's local training.
        local_model.compile(
            optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
            loss=tf.keras.losses.SparseCategoricalCrossentropy(
                from_logits=True
            ),
        )
        history = local_model.fit(
            get_features(rows), labels[rows],
            epochs=LOCAL_EPOCHS, batch_size=LOCAL_BATCH,
            shuffle=True, verbose=0,
        )
        loss = float(history.history["loss"][-1])
        assert np.isfinite(loss)
        upload = copy_weights(local_model)
        assert all(np.isfinite(value).all() for value in upload)
        uploads.append(upload)
        client_ids.append(client_id)
        losses.append(loss)
        print(f"  client={client_id:02d}, loss={loss:.4f}", flush=True)

    flat_weights = np.stack([
        np.concatenate([value.ravel() for value in upload])
        for upload in uploads
    ])
    detector_seed = SEED + cluster_index
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


# Fixed pretrained master teacher for the warm-start diagnostic.
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

teacher_name = "master"
teacher_snapshot = build_model("master", len(feature_names), len(classes))
with np.load(master_weights_path, allow_pickle=False) as saved:
    teacher_snapshot.set_weights([
        saved[key] for key in sorted(saved.files)
    ])
print("\nWarm-start teacher: master", flush=True)

for architecture in architectures:
    model = models[architecture]
    record = cluster_reports[architecture]
    skip_reason = None

    if record["retained_previous_model"]:
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
        seed=SEED + architectures.index(architecture),
    )
    candidate_metrics = evaluate(
        model, validation_features, validation_labels, classes
    )
    # Original warm-start behaviour: commit master KD directly.
    accepted = True
    record["kd"] = {
        "performed": True,
        "epoch_losses": kd_losses,
        "candidate_validation": candidate_metrics,
        "accepted": accepted,
    }
    record["post_kd_validation"] = (
        candidate_metrics if accepted else record["pre_kd_validation"]
    )
    record["kd"]["acceptance_policy"] = "unconditional_warm_start"
    print(
        f"{architecture}: KD accepted={accepted}, "
        f"candidate accuracy={candidate_metrics['accuracy']:.4f}, "
        f"committed accuracy="
        f"{record['post_kd_validation']['accuracy']:.4f}",
        flush=True,
    )

output_dir.mkdir(parents=True)
for architecture, model in models.items():
    np.savez_compressed(
        output_dir / f"{architecture}_weights.npz",
        **{
            f"tensor_{index:02d}": value
            for index, value in enumerate(model.get_weights())
        },
    )

report = {
    "status": "integration_check_completed",
    "seed": SEED,
    "attack": None,
    "ensemble": "three_detectors_strict",
    "aggregation": "coordinate_wise_median",
    "phase": "single_master_warm_start_round",
    "master_pretraining_performed": False,
    "pretrained_master_loaded": True,
    "master_weights_sha256": sha256(master_weights_path),
    "master_warm_start_performed": True,
    "local_epochs": LOCAL_EPOCHS,
    "local_batch_size": LOCAL_BATCH,
    "learning_rate": LEARNING_RATE,
    "kd_epochs": KD_EPOCHS,
    "kd_temperature": 3.0,
    "kd_batch_size": KD_BATCH,
    "kd_rows_used": selected_kd_rows.tolist(),
    "teacher": teacher_name,
    "teacher_selection": "fixed_pretrained_master",
    "clusters": cluster_reports,
    "test_evaluated": False,
    "final_protocol_frozen": False,
    "preprocessing_provenance_verified": False,
    "source_sha256": sha256(source),
    "client_manifest_sha256": sha256(client_dir / "manifest.json"),
    "script_sha256": sha256(Path(__file__)),
}
(output_dir / "report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print("\nBENIGN MASTER WARM-START DIAGNOSTIC: PASS")
print("Test evaluated: NO")
print("Full S4 protocol implemented: NO")
print(f"Saved: {output_dir / 'report.json'}")
