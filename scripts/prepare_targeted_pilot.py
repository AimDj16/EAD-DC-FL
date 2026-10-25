import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ATTACK_SEED = 142
source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
client_dir = Path("data/clients/idsiot2024/development_iid_seed42")
partition_dir = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2"
)
output_dir = Path("data/attacks/idsiot2024/malware_to_normal_seed142")

if output_dir.exists():
    raise FileExistsError(f"{output_dir} already exists.")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


clients = read_json(client_dir / "manifest.json")
partitions = read_json(partition_dir / "manifest.json")
assert sha256(source).lower() == partitions["source_sha256"].lower()
assert (
    sha256(client_dir / "client_indices.npz")
    == clients["client_indices_sha256"]
)
assert (
    sha256(partition_dir / "indices.npz")
    == clients["partition_indices_sha256"]
)

target_column = partitions["protocol"]["target_column"]
labels = pd.read_csv(source, usecols=[target_column])[target_column]
classes = partitions["classes"]
source_class = "Malware"
destination_class = "Normal"
assert source_class in classes and destination_class in classes

rng = np.random.default_rng(ATTACK_SEED)
malicious_ids = []
for architecture in ("small", "medium", "deep"):
    members = [
        record["client_id"] for record in clients["clients"]
        if record["architecture"] == architecture
    ]
    assert len(members) == 10
    malicious_ids.extend(
        int(value) for value in rng.choice(members, 3, replace=False)
    )
malicious_ids.sort()

poison_arrays = {}
records = []
with np.load(client_dir / "client_indices.npz", allow_pickle=False) as saved:
    for client_id in malicious_ids:
        rows = saved[f"client_{client_id:02d}"]
        poison_rows = rows[
            labels.iloc[rows].to_numpy() == source_class
        ]
        assert len(poison_rows) > 0
        poison_arrays[f"client_{client_id:02d}"] = poison_rows
        architecture = next(
            item["architecture"] for item in clients["clients"]
            if item["client_id"] == client_id
        )
        records.append({
            "client_id": client_id,
            "architecture": architecture,
            "poisoned_rows": int(len(poison_rows)),
        })

all_poison_rows = np.concatenate(list(poison_arrays.values()))
assert len(np.unique(all_poison_rows)) == len(all_poison_rows)

with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
    assert np.isin(all_poison_rows, saved["client_training"]).all()
    for name in ("server_kd", "server_validation", "test"):
        assert np.intersect1d(all_poison_rows, saved[name]).size == 0

# Verify the operator changes exactly the intended labels.
original = labels.iloc[all_poison_rows].to_numpy()
poisoned = original.copy()
poisoned[:] = destination_class
assert (original == source_class).all()
assert (poisoned == destination_class).all()
assert np.array_equal(
    labels.iloc[all_poison_rows].to_numpy(), original
)

output_dir.mkdir(parents=True)
rows_path = output_dir / "poison_rows.npz"
np.savez_compressed(rows_path, **poison_arrays)

protocol = {
    "status": "development_pilot_not_frozen",
    "attack": "targeted_label_flipping",
    "selection_seed": ATTACK_SEED,
    "source_class": source_class,
    "destination_class": destination_class,
    "source_class_id": classes.index(source_class),
    "destination_class_id": classes.index(destination_class),
    "malicious_client_ids": malicious_ids,
    "malicious_clients_per_architecture": 3,
    "malicious_fraction": 0.30,
    "source_label_poison_fraction": 1.0,
    "attack_rounds": [1, 2, 3, 4],
    "poisoning_scope": "local_training_labels_only",
    "server_data_poisoned": False,
    "evaluation_labels_poisoned": False,
    "source_file_modified": False,
    "source_sha256": sha256(source),
    "client_manifest_sha256": sha256(client_dir / "manifest.json"),
    "poison_rows_sha256": sha256(rows_path),
    "clients": records,
    "targeted_metric": {
        "numerator": "clean Malware rows predicted as Normal",
        "denominator": "all clean Malware evaluation rows",
        "effect": "attack TMR minus matched benign TMR",
    },
    "training_performed": False,
}
(output_dir / "protocol.json").write_text(
    json.dumps(protocol, indent=2), encoding="utf-8"
)

print(f"Attack: {source_class} -> {destination_class}")
print(f"Compromised client IDs: {malicious_ids}")
for record in records:
    print(
        f"  {record['architecture']:6s} client={record['client_id']:02d}: "
        f"poisoned rows={record['poisoned_rows']}"
    )
print(f"Total poisoned training rows: {len(all_poison_rows)}")
print("ATTACK ALLOCATION CHECKS: PASS")
print("Training performed: NO")
print(f"Saved: {output_dir / 'protocol.json'}")
