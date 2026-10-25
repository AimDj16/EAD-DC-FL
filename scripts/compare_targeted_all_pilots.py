import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, str(Path("src").resolve()))
from ead_dc_fl.models_and_kd import build_model

root = Path("outputs/development")
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--ead", choices=["on", "off"], required=True)
parser.add_argument("--kd", choices=["on", "off"], required=True)
args = parser.parse_args()

benign_folder = (
    "multiround_original_seed42"
    if args.ead == "on" and args.kd == "on"
    else f"ablation_original_ead_{args.ead}_kd_{args.kd}_seed42"
)
benign_dir = root / benign_folder
attack_dir = root / (
    f"targeted_attack_original_ead_{args.ead}_kd_{args.kd}_seed42"
)
partition_dir = Path(
    "data/partitions/idsiot2024/candidate_seed42_groups2"
)
client_dir = Path("data/clients/idsiot2024/development_iid_seed42")
source = Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


benign = read_json(benign_dir / "report.json")
attack = read_json(attack_dir / "report.json")
manifest = read_json(partition_dir / "manifest.json")
clients = read_json(client_dir / "manifest.json")

assert benign["status"] == attack["status"] == "completed"
for key in (
    "seed", "planned_rounds", "mode", "ensemble", "aggregation",
    "local_epochs", "local_batch_size", "learning_rate",
    "kd_epochs", "kd_batch_size", "kd_temperature", "kd_rows_used",
    "source_sha256", "client_manifest_sha256",
    "master_weights_sha256", "models_and_kd_sha256",
):
    assert benign[key] == attack[key], f"Mismatch: {key}"

assert sha256(source).lower() == benign["source_sha256"].lower()
assert sha256(client_dir / "manifest.json") == benign["client_manifest_sha256"]
assert (
    sha256(partition_dir / "indices.npz")
    == clients["partition_indices_sha256"]
)
assert (
    sha256(client_dir / "normalisation.npz")
    == clients["normalisation_sha256"]
)
assert (
    sha256(Path("src/ead_dc_fl/models_and_kd.py"))
    == benign["models_and_kd_sha256"]
)

classes = manifest["classes"]
feature_names = manifest["feature_names"]
target = manifest["protocol"]["target_column"]

with np.load(partition_dir / "indices.npz", allow_pickle=False) as saved:
    rows = saved["server_validation"].copy()
with np.load(client_dir / "normalisation.npz", allow_pickle=False) as saved:
    mean = saved["mean"].copy()
    scale = saved["scale"].copy()

frame = pd.read_csv(source)
validation = frame.iloc[rows]
malware_mask = validation[target].to_numpy() == "Malware"
X = (
    (validation.loc[malware_mask, feature_names].to_numpy(dtype=np.float64)
     - mean) / scale
).astype(np.float32)
assert np.isfinite(X).all()
assert len(X) > 0
del frame, validation

results = []
for benign_round, attack_round in zip(benign["rounds"], attack["rounds"]):
    round_number = benign_round["round"]
    assert round_number == attack_round["round"]
    print(f"\nROUND {round_number}")

    for architecture in ("small", "medium", "deep"):
        checkpoint = (
            benign_dir / f"round_{round_number:02d}"
            / f"{architecture}_weights.npz"
        )
        assert (
            sha256(checkpoint)
            == benign_round["checkpoint_hashes"][architecture]
        )

        model = build_model(architecture, len(feature_names), len(classes))
        with np.load(checkpoint, allow_pickle=False) as saved:
            model.set_weights([saved[key] for key in sorted(saved.files)])

        predictions = []
        for start in range(0, len(X), 256):
            logits = model(X[start:start + 256], training=False).numpy()
            assert np.isfinite(logits).all()
            predictions.append(logits.argmax(axis=1))
        predictions = np.concatenate(predictions)

        benign_hits = int((predictions == classes.index("Normal")).sum())
        benign_tmr = benign_hits / len(X)
        attacked = attack_round["clusters"][architecture]
        attack_metrics = attacked["post_kd_validation"]
        assert attack_metrics["targeted_source_rows"] == len(X)
        attack_tmr = attack_metrics["targeted_misclassification_rate"]
        baseline_metrics = benign_round["clusters"][architecture][
            "post_kd_validation"
        ]

        row = {
            "round": round_number,
            "architecture": architecture,
            "source_rows": int(len(X)),
            "benign_targeted_hits": benign_hits,
            "attack_targeted_hits": attack_metrics["targeted_hits"],
            "benign_tmr": benign_tmr,
            "attack_tmr": attack_tmr,
            "delta_tmr": attack_tmr - benign_tmr,
            "accuracy_drop_pp": 100 * (
                baseline_metrics["accuracy"] - attack_metrics["accuracy"]
            ),
            "macro_f1_drop": (
                baseline_metrics["macro_f1"] - attack_metrics["macro_f1"]
            ),
            "attack_pre_kd_tmr": attacked["pre_kd_validation"][
                "targeted_misclassification_rate"
            ],
            "screening_audit": attacked["screening_audit"],
        }
        results.append(row)
        print(
            f"{architecture}: benign TMR={benign_tmr:.4f}, "
            f"attack TMR={attack_tmr:.4f}, "
            f"delta={100 * row['delta_tmr']:+.2f} pp, "
            f"accuracy drop={row['accuracy_drop_pp']:+.2f} pp"
        )
        del model

output = root / (
    f"targeted_comparison_ead_{args.ead}_kd_{args.kd}_seed42.json"
)
output.write_text(json.dumps({
    "status": "development_pilot_comparison",
    "ead": args.ead,
    "kd": args.kd,
    "metric": "Malware-to-Normal targeted misclassification rate",
    "evaluation_partition": "server_validation",
    "results": results,
    "test_evaluated": False,
    "limitation": "One seed, four rounds, development partition.",
}, indent=2), encoding="utf-8")

print("\nMATCHED TARGETED COMPARISON: PASS")
print(f"Saved: {output}")
