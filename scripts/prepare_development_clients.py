import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


SEED = 42
CLIENT_COUNT = 30

source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
partition_dir = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2"
)
output_dir = Path("data/clients/idsiot2024/development_iid_seed42")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if output_dir.exists():
    raise FileExistsError(
        f"{output_dir} already exists. Existing allocations are preserved."
    )

manifest = json.loads(
    (partition_dir / "manifest.json").read_text(encoding="utf-8-sig")
)
assert sha256(source).lower() == manifest["source_sha256"].lower()
assert (
    sha256(partition_dir / "indices.npz").lower()
    == manifest["indices_sha256"].lower()
)

with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
    partitions = {
        name: saved[name].copy()
        for name in manifest["partition_order"]
    }

frame = pd.read_csv(source)
features = manifest["feature_names"]
classes = manifest["classes"]
target = manifest["protocol"]["target_column"]

assert len(frame) == manifest["rows"]
assert len(features) == 96
assert len(classes) == 7

X = frame[features].to_numpy(dtype=np.float64)
label_mapping = {name: index for index, name in enumerate(classes)}
encoded = frame[target].map(label_mapping)
assert encoded.notna().all()
y = encoded.to_numpy(dtype=np.int64)
assert np.isfinite(X).all()

# Fit only on client-training rows.
# Prior preprocessing of the supplied CSV remains unverified.
training_rows = partitions["client_training"]
scaler = StandardScaler().fit(X[training_rows])
assert np.isfinite(scaler.mean_).all()
assert np.isfinite(scaler.scale_).all()
assert (scaler.scale_ > 0).all()

# Allocate every training row once, class by class.
rng = np.random.default_rng(SEED)
client_rows = [[] for _ in range(CLIENT_COUNT)]

for class_id in range(len(classes)):
    rows = training_rows[y[training_rows] == class_id].copy()
    rng.shuffle(rows)

    # Rotate recipients so remainder rows do not favour one architecture.
    recipients = rng.permutation(CLIENT_COUNT)
    for recipient, chunk in zip(
        recipients, np.array_split(rows, CLIENT_COUNT)
    ):
        client_rows[int(recipient)].extend(chunk.tolist())

client_arrays = {}
client_records = []

for client_id, rows in enumerate(client_rows):
    rows = np.asarray(rows, dtype=np.int64)
    rng.shuffle(rows)
    architecture = ("small", "medium", "deep")[client_id % 3]
    counts = np.bincount(y[rows], minlength=len(classes))

    assert len(rows) > 0
    assert (counts > 0).all()
    client_arrays[f"client_{client_id:02d}"] = rows
    client_records.append({
        "client_id": client_id,
        "architecture": architecture,
        "rows": int(len(rows)),
        "class_counts": {
            name: int(counts[index])
            for index, name in enumerate(classes)
        },
    })

allocated = np.concatenate(list(client_arrays.values()))
assert len(np.unique(allocated)) == len(allocated)
assert np.array_equal(np.sort(allocated), np.sort(training_rows))

for name in ("server_kd", "server_validation", "test"):
    assert np.intersect1d(allocated, partitions[name]).size == 0

# Check transformed training data without transforming the test partition.
normalised_training = scaler.transform(X[training_rows])
assert np.isfinite(normalised_training).all()

output_dir.mkdir(parents=True)
client_path = output_dir / "client_indices.npz"
normalisation_path = output_dir / "normalisation.npz"

np.savez_compressed(client_path, **client_arrays)
np.savez_compressed(
    normalisation_path,
    mean=scaler.mean_,
    scale=scaler.scale_,
    variance=scaler.var_,
    samples_seen=np.asarray(scaler.n_samples_seen_),
)

report = {
    "status": "development_not_frozen",
    "seed": SEED,
    "allocation": "class_stratified_row_allocation",
    "client_count": CLIENT_COUNT,
    "clients_per_architecture": {
        name: sum(c["architecture"] == name for c in client_records)
        for name in ("small", "medium", "deep")
    },
    "source_sha256": sha256(source),
    "partition_indices_sha256": sha256(partition_dir / "indices.npz"),
    "client_indices_sha256": sha256(client_path),
    "normalisation_sha256": sha256(normalisation_path),
    "feature_names": features,
    "classes": classes,
    "normalisation_fit_partition": "client_training",
    "preprocessing_provenance_verified": False,
    "identical_features_may_span_training_clients": True,
    "clients": client_records,
    "checks": {
        "every_training_row_allocated_once": True,
        "no_server_or_test_rows_in_clients": True,
        "all_classes_present_in_every_client": True,
        "finite_training_normalisation": True,
    },
    "training_performed": False,
    "test_features_transformed": False,
}
(output_dir / "manifest.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

for architecture in ("small", "medium", "deep"):
    members = [
        c for c in client_records
        if c["architecture"] == architecture
    ]
    sizes = [c["rows"] for c in members]
    print(
        f"{architecture}: clients={len(members)}, "
        f"rows={sum(sizes)}, size_range={min(sizes)}-{max(sizes)}"
    )

print(f"Normalisation fitted on: {len(training_rows)} training rows")
print("CLIENT ALLOCATION AND NORMALISATION CHECKS: PASS")
print("Training performed: NO")
print("Test features transformed: NO")
print(f"Saved: {output_dir}")
