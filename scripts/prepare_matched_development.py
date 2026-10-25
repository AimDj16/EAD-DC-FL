"""Create saved initial models and fixed cohorts once for paired development runs."""
import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ead_dc_fl.models_and_kd import build_model
from ead_dc_fl.matched_experiments import array_sha256, canonical_sha256, file_sha256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path("data/experiments/idsiot2024/matched_seed42_v1"))
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError("Shared initial states already exist; preserve them: " + str(args.output))

partition = Path("data/partitions/idsiot2024/candidate_seed42_groups2")
clients = Path("data/clients/idsiot2024/development_iid_seed42")
master = Path("outputs/development/master_pretrain_seed42")
attack = Path("data/attacks/idsiot2024/malware_to_normal_seed142")
source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

pm, cm, mr, ap = (read(directory / filename) for directory, filename in (
    (partition, "manifest.json"), (clients, "manifest.json"),
    (master, "report.json"), (attack, "protocol.json")))
paths = [source, partition / "manifest.json", partition / "indices.npz",
         clients / "manifest.json", clients / "client_indices.npz", clients / "normalisation.npz",
         master / "report.json", master / "master_weights.npz",
         attack / "protocol.json", attack / "poison_rows.npz",
         Path("src/ead_dc_fl/models_and_kd.py"), Path("src/ead_dc_fl/attacks.py"),
         Path("src/ead_dc_fl/matched_experiments.py")]
hashes = {path.as_posix(): file_sha256(path) for path in paths}
checks = [(source, pm["source_sha256"]), (source, mr["source_sha256"]),
          (source, ap["source_sha256"]),
          (partition / "indices.npz", pm["indices_sha256"]),
          (partition / "indices.npz", cm["partition_indices_sha256"]),
          (partition / "indices.npz", mr["partition_indices_sha256"]),
          (clients / "client_indices.npz", cm["client_indices_sha256"]),
          (clients / "normalisation.npz", cm["normalisation_sha256"]),
          (clients / "normalisation.npz", mr["normalisation_sha256"]),
          (master / "master_weights.npz", mr["weights_sha256"]),
          (clients / "manifest.json", ap["client_manifest_sha256"]),
          (attack / "poison_rows.npz", ap["poison_rows_sha256"])]
for path, expected in checks:
    if hashes[path.as_posix()] != expected.lower():
        raise ValueError("Input checksum mismatch: " + str(path))
if not (cm["classes"] == mr["classes"] == pm["classes"]
        and cm["feature_names"] == mr["feature_names"] == pm["feature_names"]):
    raise ValueError("Feature/label definitions differ.")
architectures = ("small", "medium", "deep")
cohort = {name: sorted(int(item["client_id"]) for item in cm["clients"]
                      if item["architecture"] == name) for name in architectures}
if any(len(ids) != 10 for ids in cohort.values()) or len(set(sum(cohort.values(), []))) != 30:
    raise ValueError("Expected 30 distinct clients, ten per architecture.")
with np.load(clients / "client_indices.npz", allow_pickle=False) as saved:
    registered_keys = {f"client_{cid:02d}" for ids in cohort.values() for cid in ids}
    if set(saved.files) != registered_keys:
        raise ValueError("Allocation keys do not match the client registry.")
    rows = np.concatenate([saved[key] for key in sorted(saved.files)])
    counts = {key: int(len(saved[key])) for key in saved.files}
with np.load(partition / "indices.npz", allow_pickle=False) as saved:
    if len(np.unique(rows)) != len(rows) or not np.array_equal(np.sort(rows), np.sort(saved["client_training"])):
        raise ValueError("Client rows must cover the training pool exactly once.")
    for name in ("server_kd", "server_validation", "test"):
        if np.intersect1d(rows, saved[name]).size:
            raise ValueError("Client allocation overlaps " + name)
if any(count < 1 for count in counts.values()):
    raise ValueError("Clients must have nonempty allocations.")

tf.keras.utils.set_random_seed(42)
tf.config.experimental.enable_op_determinism()
for gpu in tf.config.list_physical_devices("GPU"):
    tf.config.experimental.set_memory_growth(gpu, True)
models = {}
args.output.mkdir(parents=True, exist_ok=False)
for index, name in enumerate(architectures):
    tf.keras.utils.set_random_seed(42 + 100 * index)
    model = build_model(name, len(pm["feature_names"]), len(pm["classes"]))
    values = model.get_weights()
    keys = [f"tensor_{number:02d}" for number in range(len(values))]
    filename = name + "_initial_weights.npz"
    np.savez_compressed(args.output / filename, **dict(zip(keys, values)))
    models[name] = {"file": filename, "sha256": file_sha256(args.output / filename),
                    "keys": keys, "tensor_sha256": [array_sha256(value) for value in values]}
manifest = {
    "schema": "matched_development_v1", "seed": 42, "rounds": 4,
    "architectures": list(architectures), "initial_models": models,
    "input_sha256": hashes, "client_manifest": (clients / "manifest.json").as_posix(),
    "client_sample_counts": counts,
    "participation": {str(number): cohort for number in range(1, 5)},
    "participation_policy": "full_participation_fixed_order",
    "training_settings": {"local_epochs": 1, "local_batch_size": 128, "learning_rate": 0.001,
                          "kd_epochs": 3, "kd_batch_size": 256, "kd_temperature": 3.0,
                          "warm_start_rounds": 3},
    "local_order_policy": "NumPy permutation per client/round; Keras shuffle=False",
    "local_seed_rule": "42 + 1000 * round + client_id + 1",
    "kd_seed_rule": "42 + 1000 * round + architecture_index",
    "initial_state_environment": {"python": platform.python_version(), "tensorflow": tf.__version__,
                                  "numpy": np.__version__},
    "final_protocol_frozen": False, "preprocessing_provenance_verified": False,
}
manifest["experiment_id"] = canonical_sha256(manifest)
(args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("MATCHED DEVELOPMENT INPUTS: CREATED")
print("Experiment ID:", manifest["experiment_id"])
print("Initial states saved; all 30 clients scheduled in the same order every round.")
print("Dataset allocations unchanged; no training performed; final protocol not frozen.")
print("Saved:", args.output / "manifest.json")
