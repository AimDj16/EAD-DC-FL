"""Matched within-architecture label-skew study; original IID runner preserved."""
import hashlib
import json
import sys
import time
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


from ead_dc_fl.matched_experiments import (
    aggregate_models, array_sha256, canonical_sha256, load_matched_experiment,
    local_training_order, restore_initial_models,
)

from ead_dc_fl.label_skew import (
    ids_metrics, verify_subset_record, verify_labelskew_contract, run_directory,
    iid_reference_directory,
)

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
# Client allocation is read from the separately registered matched contract.
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode", choices=["original"],
    required=True,
)
parser.add_argument("--ead", choices=["on", "off"], required=True)
parser.add_argument("--kd", choices=["on", "off"], required=True)
parser.add_argument("--arm", choices=["benign", "attack"], required=True)
parser.add_argument("--sigma", type=float, default=0.0)
parser.add_argument("--attack", choices=["gaussian", "targeted"], required=True)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--rounds", type=int, required=True)
parser.add_argument("--data-regime", choices=["labelskew", "iid-replay"], default="labelskew")
parser.add_argument("--iid-reference", type=Path)
parser.add_argument("--aggregation", choices=["fedavg", "median"], default="fedavg")
parser.add_argument(
    "--matched-experiment", type=Path,
    required=True,
)
args = parser.parse_args()
if not 0 <= args.seed < 1000000 or not 4 <= args.rounds <= 1000:
    parser.error("Require seed in [0,1000000) and rounds in [4,1000].")
if args.aggregation != "fedavg" or args.mode != "original":
    parser.error("This programme uses FedAvg and original KD policy only.")
if args.rounds != 12 or args.seed not in (42, 2026, 31415):
    parser.error("Use the existing three seeds and 12-round input contracts.")
if args.arm == "attack" and args.attack != "targeted":
    parser.error("This bounded stage studies Malware-to-Normal label flipping.")
if args.arm == "benign" and args.attack != "gaussian":
    parser.error("Benign controls use the original Gaussian-runner sigma0 branch.")
if args.data_regime == "iid-replay" and (
    args.seed != 42 or args.arm != "benign" or args.ead != "on"
    or args.kd != "on" or args.iid_reference is None
):
    parser.error("IID fidelity diagnostic is seed42 benign EAD/KD on with --iid-reference.")
if args.data_regime == "labelskew" and args.iid_reference is not None:
    parser.error("--iid-reference is only valid for the bounded IID fidelity replay.")
if (args.arm == "benign" or args.attack == "targeted") and args.sigma != 0:
    parser.error("Benign/targeted conditions require sigma0.")
if args.attack == "gaussian" and args.arm == "attack" and args.sigma <= 0:
    parser.error("Gaussian attack requires a positive sigma.")
SEED = args.seed
if not np.isfinite(args.sigma) or args.sigma < 0:
    parser.error("--sigma must be finite and non-negative.")
sigma_tag = str(args.sigma).replace(".", "p")
NOISE_SEED = SEED + 200
from ead_dc_fl.attacks import gaussian_weight_poisoning
CONTRACT_ROUNDS = args.rounds
ROUNDS = 4 if args.data_regime == "iid-replay" else CONTRACT_ROUNDS
WARM_START_ROUNDS = 3
# Output directory assigned from the registered allocation and experiment ID.


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
        **ids_metrics(labels, predictions, classes),
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
        scores = np.asarray(detector.decision_function(scaled))
        labels = np.asarray(detector.predict(scaled), dtype=int)
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


training_settings = {
    "local_epochs": LOCAL_EPOCHS, "local_batch_size": LOCAL_BATCH,
    "learning_rate": LEARNING_RATE, "kd_epochs": KD_EPOCHS,
    "kd_batch_size": KD_BATCH, "kd_temperature": 3.0,
    "warm_start_rounds": WARM_START_ROUNDS,
}
matched = (
    verify_labelskew_contract(args.matched_experiment, SEED, CONTRACT_ROUNDS)
    if args.data_regime == "labelskew" else
    load_matched_experiment(args.matched_experiment, SEED, CONTRACT_ROUNDS, training_settings)
)
client_dir = Path(matched["client_manifest"]).parent
output_dir = (
    run_directory(matched, args.arm, args.ead, args.kd) if args.data_regime == "labelskew"
    else Path("outputs/checks/labelskew_runner_iid_replay_seed42_v1")
)

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

initial_state_sha256 = restore_initial_models(models, matched, args.matched_experiment)

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
selection_path = Path(matched.get(
    "attack_protocol", "data/attacks/idsiot2024/malware_to_normal_seed142/protocol.json"
))
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
    "attack_rounds": list(range(1, ROUNDS + 1)),
    "training_labels_poisoned": False,
    "server_data_poisoned": False,
    "final_sigma_selected": False,
}


poison_rows = {}
if args.attack == "targeted":
    attack_protocol = dict(selection)
    attack_protocol["attack_rounds"] = list(range(1, ROUNDS + 1))
    attack_protocol["original_selection_protocol_sha256"] = sha256(selection_path)
    attack_protocol["training_performed"] = False  # inherited definition, not run status
    attack_protocol["scope_note"] = "Attack definition; actual execution is in upload_diagnostics and run status"
    poison_path = selection_path.parent / "poison_rows.npz"
    if sha256(poison_path) != selection["poison_rows_sha256"]:
        raise ValueError("Saved poison rows changed.")
    with np.load(poison_path, allow_pickle=False) as saved:
        poison_rows = {k:saved[k].copy() for k in saved.files}
    for cid in malicious_ids:
        key = f"client_{cid:02d}"
        assert np.isin(poison_rows[key],allocations[key]).all()
        assert (labels[poison_rows[key]] == selection["source_class_id"]).all()

iid_reference = None
base_iid_reference_path = None
if args.data_regime == "labelskew":
    base = read_json(Path(matched["base_iid_experiment_manifest"]))
    base_iid_reference_path = iid_reference_directory(base, args.arm, args.ead, args.kd) / "report.json"
    base_reference = read_json(base_iid_reference_path)
    if (base_reference["status"] != "completed" or base_reference["matched_experiment_id"] != base["experiment_id"]
            or base_reference["script_sha256"] != sha256(Path("scripts/run_matched_replication.py"))
            or base_reference["seed"] != SEED or base_reference["arm"] != args.arm
            or base_reference["ead_enabled"] != (args.ead == "on")
            or base_reference["kd_enabled"] != (args.kd == "on")
            or base_reference["mode"] != "original"):
        raise ValueError("Existing IID comparison reference is incomplete or different.")
if args.iid_reference:
    iid_reference = read_json(args.iid_reference / "report.json")
    if (iid_reference["status"] != "completed" or iid_reference["seed"] != SEED
        or iid_reference["planned_rounds"] != CONTRACT_ROUNDS
        or iid_reference["matched_experiment_id"] != matched["experiment_id"]
        or not iid_reference["ead_enabled"] or not iid_reference["kd_enabled"]
        or iid_reference["mode"] != "original" or iid_reference["arm"] != "benign"
        or iid_reference["script_sha256"] != sha256(Path("scripts/run_matched_replication.py"))):
        raise ValueError("Require the completed original seed42 combined benign reference.")
    for number in range(1, ROUNDS + 1):
        for architecture in architectures:
            path = args.iid_reference / f"round_{number:02d}" / f"{architecture}_weights.npz"
            if sha256(path) != iid_reference["rounds"][number - 1]["checkpoint_hashes"][architecture]:
                raise ValueError("IID reference checkpoint changed: " + str(path))

output_dir.mkdir(parents=True)
run_report = {
    "status": "running",
    "configuration_id": "matched_labelskew_development_v1",
    "data_regime": args.data_regime,
    "execution_purpose": "iid_fidelity_replay" if iid_reference else "labelskew_development",
    "scientific_run_count": 0 if iid_reference else 1,
    "contract_rounds": CONTRACT_ROUNDS,
    "allocation_version": matched.get("allocation_version"),
    "allocation_seed": matched.get("allocation_seed"),
    "dirichlet_alpha": matched.get("dirichlet_alpha"),
    "base_iid_experiment_id": matched.get("base_iid_experiment_id", matched["experiment_id"]),
    "base_iid_reference_report": str(base_iid_reference_path) if base_iid_reference_path else None,
    "base_iid_reference_report_sha256": sha256(base_iid_reference_path) if base_iid_reference_path else None,
    "label_skew_module_sha256": sha256(Path("src/ead_dc_fl/label_skew.py")),
    "designated_vs_effective_attack_note": "screening_audit uses fixed designated compromised IDs; effective_poisoning_screening_audit separately records clients with actual label changes",
    "iid_reference_report_sha256": sha256(args.iid_reference / "report.json") if iid_reference else None,
    "detector_prediction_api": "predict_and_decision_function_on_fitted_cohort",
    "calibration_policy": "per_round_count_range_gt_zero_020_to_030_immediate_rerun",
    "replication_scope": matched["replication_scope"],
    "fixed_data_partition_seed": 42, "fixed_master_pretraining_seed": 42,
    "gaussian_noise_seed": NOISE_SEED,
    "iid_replay_checks": [],
    "matched_experiment_id": matched["experiment_id"],
    "matched_experiment_manifest": args.matched_experiment.as_posix() + "/manifest.json",
    "initial_state_sha256": initial_state_sha256,
    "participation_policy": matched["participation_policy"],
    "training_settings": training_settings,
    "execution_environment": {
        "python": sys.version, "tensorflow": tf.__version__, "numpy": np.__version__,
    },
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
    "aggregation": (
        "sample_weighted_fedavg" if args.aggregation == "fedavg"
        else "coordinate_wise_median"
    ),
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
if iid_reference:
    for key in ("initial_state_sha256", "training_settings", "execution_environment",
                "source_sha256", "client_manifest_sha256", "master_weights_sha256",
                "models_and_kd_sha256", "attack_operator_sha256", "kd_rows_used"):
        if run_report[key] != iid_reference[key]:
            raise ValueError("IID replay input differs: " + key)
run_started = time.perf_counter()
for round_number in range(1, ROUNDS + 1):
    round_started = time.perf_counter()
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
        members_by_id = {member["client_id"]: member for member in members}
        members = [members_by_id[cid] for cid in matched["participation"][str(round_number)][architecture]]
        assert len(members) == 10

        local_model = build_model(
            architecture, len(feature_names), len(classes)
        )
        local_training_orders = {}
        uploads = []
        client_ids = []
        losses = []
        upload_diagnostics = []

        print(f"\nTraining {architecture} clients...", flush=True)
        for member in members:
            client_id = member["client_id"]
            tf.keras.utils.set_random_seed(SEED + 1000 * round_number + client_id + 1)
            rows = allocations[f"client_{client_id:02d}"]
            local_order = local_training_order(
                len(rows), SEED + 1000 * round_number + client_id + 1,
            )
            local_training_orders[str(client_id)] = array_sha256(rows[local_order])
            local_model.set_weights(initial_weights)

            # Fresh optimiser for each client's local training.
            local_model.compile(
                optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
                loss=tf.keras.losses.SparseCategoricalCrossentropy(
                    from_logits=True
                ),
            )
            local_labels = labels[rows].copy()
            active_attack = (args.arm == "attack" and client_id in malicious_ids
                             and round_number in attack_protocol["attack_rounds"])
            poisoned_count = 0
            if active_attack and args.attack == "targeted":
                mask = np.isin(rows,poison_rows[f"client_{client_id:02d}"])
                assert (local_labels[mask] == selection["source_class_id"]).all()
                local_labels[mask] = selection["destination_class_id"]
                assert np.array_equal(local_labels[~mask],labels[rows][~mask])
                poisoned_count = int(mask.sum())
                assert poisoned_count == len(poison_rows[f"client_{client_id:02d}"])
            else:
                assert np.array_equal(local_labels, labels[rows])

            history = local_model.fit(
                get_features(rows)[local_order], local_labels[local_order],
                epochs=LOCAL_EPOCHS, batch_size=LOCAL_BATCH,
                shuffle=False, verbose=0,
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
                "poisoning_applied": bool(active_attack and poisoned_count > 0),
                "designated_malicious_client": bool(active_attack),
                "source_class_rows_available": int(np.sum(labels[rows] == selection["source_class_id"])),
                "poisoned_label_rows": poisoned_count,
                "training_labels_original_sha256": array_sha256(labels[rows]),
                "training_labels_used_sha256": array_sha256(local_labels),
                "submitted_tensor_sha256": [array_sha256(value) for value in upload],
            }
            if active_attack and args.attack == "gaussian":
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
            aggregate = aggregate_models(
                [uploads[position] for position in accepted_positions],
                [len(allocations[f"client_{client_ids[position]:02d}"])
                 for position in accepted_positions],
                rule=args.aggregation,
            )
            server_model.set_weights(aggregate)
            eligible_teachers.append(architecture)

        pre_kd = evaluate(
            server_model, validation_features, validation_labels, classes
        )
        cluster_reports[architecture] = {
            "client_ids": client_ids,
            "local_training_order_sha256": local_training_orders,
            "accepted_sample_counts": {
                str(client_ids[position]): int(len(allocations[f"client_{client_ids[position]:02d}"]))
                for position in accepted_positions
            },
            "fedavg_coefficients": ({
                str(client_ids[position]): float(
                    len(allocations[f"client_{client_ids[position]:02d}"]) /
                    sum(len(allocations[f"client_{client_ids[p]:02d}"]) for p in accepted_positions)
                ) for position in accepted_positions
            } if args.aggregation == "fedavg" and not fallback else None),
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
            "aggregation_output_tensor_sha256": [array_sha256(value) for value in server_model.get_weights()],
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
        effective = {item["client_id"] for item in record["upload_diagnostics"]
                     if item["poisoning_applied"]}
        record["effective_poisoning_screening_audit"] = {
            "effective_poisoned_client_ids": sorted(effective),
            "effective_poisoned_rejected": sorted(effective & rejected_ids),
            "effective_poisoned_accepted": sorted(effective - rejected_ids),
            "designated_zero_opportunity_client_ids": sorted(compromised - effective),
            "total_poisoned_label_rows": sum(item["poisoned_label_rows"] for item in record["upload_diagnostics"]),
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

    actual_participation = {
        name: cluster_reports[name]["client_ids"] for name in architectures
    }
    if actual_participation != matched["participation"][str(round_number)]:
        raise RuntimeError("Actual participation differs from the shared schedule.")
    round_report = {
        "round_seconds": time.perf_counter() - round_started,
        "round": round_number,
        "participation": actual_participation,
        "participation_sha256": canonical_sha256(actual_participation),
        "phase": "master_warm_start" if warm_phase else "adaptive",
        "teacher": teacher_name,
        "teacher_tie_breaking": list(architectures),
        "clusters": cluster_reports,
        "checkpoint_hashes": checkpoint_hashes,
    }
    if iid_reference:
        expected = iid_reference["rounds"][round_number - 1]
        try:
            for key in ("teacher", "phase", "participation", "participation_sha256",
                        "teacher_tie_breaking", "clusters"):
                verify_subset_record(round_report[key], expected[key], key)
            for architecture in architectures:
                path = args.iid_reference / f"round_{round_number:02d}" / f"{architecture}_weights.npz"
                with np.load(path, allow_pickle=False) as saved:
                    values = models[architecture].get_weights()
                    keys = [f"tensor_{i:02d}" for i in range(len(values))]
                    if sorted(saved.files) != keys or not all(
                        a.dtype == saved[k].dtype and a.shape == saved[k].shape
                        and np.array_equal(a, saved[k]) for a, k in zip(values, keys)):
                        raise ValueError("IID replay tensor mismatch: " + architecture)
        except ValueError as error:
            run_report["status"] = "iid_replay_failed"
            run_report["verification_error"] = str(error)
            (output_dir / "report.json").write_text(json.dumps(run_report, indent=2))
            raise
        run_report["iid_replay_checks"].append({
            "round": round_number, "original_records_exact": True, "checkpoint_tensors_exact": True,
        })
        print(f"IID RUNNER FIDELITY ROUND {round_number}: EXACT MATCH", flush=True)
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

run_report["elapsed_seconds"] = time.perf_counter() - run_started
run_report["status"] = "iid_replay_completed" if iid_reference else "completed"
(output_dir / "report.json").write_text(
    json.dumps(run_report, indent=2), encoding="utf-8"
)
print("\nIID FIDELITY REPLAY: COMPLETE" if iid_reference else "\nMATCHED LABEL-SKEW DEVELOPMENT RUN: COMPLETE")
print(f"Sigma: {args.sigma}")
print("Final sigma selected: NO")
print(f"Mode: {args.mode}")
print("Test evaluated: NO")
print("Final protocol frozen: NO")
print(f"Saved: {output_dir / 'report.json'}")

