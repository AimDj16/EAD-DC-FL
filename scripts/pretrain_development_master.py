import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, recall_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.models_and_kd import build_model

SEED = 42
EPOCHS = 20
BATCH_SIZE = 256
LEARNING_RATE = 0.001

source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
partition_dir = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2"
)
client_dir = Path("data/clients/idsiot2024/development_iid_seed42")
output_dir = Path("outputs/development/master_pretrain_seed42")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


if output_dir.exists():
    raise FileExistsError(
        f"{output_dir} already exists. Existing results are preserved."
    )

tf.keras.utils.set_random_seed(SEED)
tf.config.experimental.enable_op_determinism()

manifest = read_json(partition_dir / "manifest.json")
client_manifest = read_json(client_dir / "manifest.json")
assert sha256(source).lower() == manifest["source_sha256"].lower()
assert (
    sha256(partition_dir / "indices.npz").lower()
    == manifest["indices_sha256"].lower()
)
assert (
    sha256(partition_dir / "indices.npz").lower()
    == client_manifest["partition_indices_sha256"].lower()
)
assert (
    sha256(client_dir / "normalisation.npz").lower()
    == client_manifest["normalisation_sha256"].lower()
)

with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
    kd_rows = saved["server_kd"].copy()
    validation_rows = saved["server_validation"].copy()

with np.load(client_dir / "normalisation.npz", allow_pickle=False) as saved:
    mean = saved["mean"].copy()
    scale = saved["scale"].copy()

assert np.intersect1d(kd_rows, validation_rows).size == 0

frame = pd.read_csv(source)
classes = manifest["classes"]
features = manifest["feature_names"]
target = manifest["protocol"]["target_column"]
mapping = {name: index for index, name in enumerate(classes)}


def extract(rows):
    selected = frame.iloc[rows]
    raw = selected[features].to_numpy(dtype=np.float64)
    X = ((raw - mean) / scale).astype(np.float32)
    encoded = selected[target].map(mapping)
    assert encoded.notna().all()
    y = encoded.to_numpy(dtype=np.int64)
    assert np.isfinite(X).all()
    return X, y


X_train, y_train = extract(kd_rows)
X_validation, y_validation = extract(validation_rows)
del frame

master = build_model("master", len(features), len(classes))
master.compile(
    optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=["accuracy"],
)

print(f"Master training rows: {len(X_train)}", flush=True)
print(f"Validation rows: {len(X_validation)}", flush=True)
print("Training master for 20 epochs...", flush=True)

history = master.fit(
    X_train, y_train,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    shuffle=True,
    verbose=2,
)

for values in history.history.values():
    assert np.isfinite(values).all()

predictions = []
for start in range(0, len(X_validation), BATCH_SIZE):
    logits = master(
        X_validation[start:start + BATCH_SIZE], training=False
    ).numpy()
    assert np.isfinite(logits).all()
    predictions.append(logits.argmax(axis=1))
predictions = np.concatenate(predictions)

recalls = recall_score(
    y_validation, predictions,
    labels=np.arange(len(classes)),
    average=None, zero_division=0,
)
metrics = {
    "accuracy": float(accuracy_score(y_validation, predictions)),
    "macro_f1": float(f1_score(
        y_validation, predictions,
        labels=np.arange(len(classes)),
        average="macro", zero_division=0,
    )),
    "per_class_recall": {
        name: float(recalls[index])
        for index, name in enumerate(classes)
    },
}

weights = master.get_weights()
assert all(np.isfinite(value).all() for value in weights)

output_dir.mkdir(parents=True)
weights_path = output_dir / "master_weights.npz"
np.savez_compressed(
    weights_path,
    **{
        f"tensor_{index:02d}": value
        for index, value in enumerate(weights)
    },
)

report = {
    "status": "development_master_pretrained",
    "seed": SEED,
    "architecture": "master",
    "hidden_layers": [1024, 512, 256],
    "feature_names": features,
    "classes": classes,
    "training_partition": "server_kd",
    "training_rows": int(len(kd_rows)),
    "epochs": EPOCHS,
    "batch_size": BATCH_SIZE,
    "optimiser": "Adam",
    "learning_rate": LEARNING_RATE,
    "checkpoint_policy": "final_epoch",
    "history": history.history,
    "validation": metrics,
    "source_sha256": sha256(source),
    "partition_indices_sha256": sha256(partition_dir / "indices.npz"),
    "normalisation_sha256": sha256(client_dir / "normalisation.npz"),
    "weights_sha256": sha256(weights_path),
    "script_sha256": sha256(Path(__file__)),
    "test_evaluated": False,
    "warm_start_performed": False,
    "final_protocol_frozen": False,
    "preprocessing_provenance_verified": False,
}
(output_dir / "report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print(f"\nMaster validation accuracy: {metrics['accuracy']:.4f}")
print(f"Master validation macro-F1: {metrics['macro_f1']:.4f}")
for name, recall in metrics["per_class_recall"].items():
    print(f"  {name} recall: {recall:.4f}")
print("MASTER PRETRAINING: PASS")
print("Test evaluated: NO")
print(f"Saved: {output_dir / 'report.json'}")
