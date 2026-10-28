"""Shared inputs, initial states and aggregation for matched development runs.

This freezes experimental inputs, not final methodology or dataset provenance.
No TensorFlow dependency is needed to verify a contract or aggregate arrays.
"""
import hashlib
import json
from pathlib import Path

import numpy as np


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def array_sha256(array):
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(json.dumps(list(value.shape)).encode("ascii"))
    digest.update(value.tobytes())
    return digest.hexdigest()


def load_matched_experiment(directory, seed, rounds, training_settings, root=Path(".")):
    """Fail before training if any registered input or initial state changed."""
    root = Path(root)
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    identifier = manifest.get("experiment_id")
    payload = {key: value for key, value in manifest.items() if key != "experiment_id"}
    if identifier != canonical_sha256(payload):
        raise ValueError("Matched experiment manifest was changed.")
    if manifest.get("schema") != "matched_development_v1":
        raise ValueError("Unsupported matched experiment schema.")
    if manifest["seed"] != seed or manifest["rounds"] != rounds:
        raise ValueError("Runner seed/rounds do not match the registered experiment.")
    if manifest["training_settings"] != training_settings:
        raise ValueError("Training settings differ from the matched experiment.")
    for name, expected in manifest["input_sha256"].items():
        if file_sha256(root / name) != expected:
            raise ValueError("Matched input changed: " + name)
    for architecture, entry in manifest["initial_models"].items():
        if file_sha256(directory / entry["file"]) != entry["sha256"]:
            raise ValueError("Initial checkpoint changed: " + architecture)
    clients = json.loads((root / manifest["client_manifest"]).read_text(encoding="utf-8-sig"))
    expected = {
        name: sorted(int(item["client_id"]) for item in clients["clients"]
                     if item["architecture"] == name)
        for name in manifest["architectures"]
    }
    if len(set(cid for ids in expected.values() for cid in ids)) != sum(map(len, expected.values())):
        raise ValueError("Client IDs are not unique.")
    schedule = manifest["participation"]
    if set(schedule) != {str(number) for number in range(1, rounds + 1)}:
        raise ValueError("Participation schedule does not cover every round.")
    for cohort in schedule.values():
        if cohort != expected:
            raise ValueError("This contract requires the same full cohort every round.")
    return manifest


def restore_initial_models(models, manifest, directory):
    if set(models) != set(manifest["initial_models"]):
        raise ValueError("Architecture registry differs from the experiment.")
    result = {}
    for architecture, model in models.items():
        entry = manifest["initial_models"][architecture]
        with np.load(Path(directory) / entry["file"], allow_pickle=False) as saved:
            if sorted(saved.files) != entry["keys"]:
                raise ValueError("Initial checkpoint tensor keys changed.")
            values = [saved[key] for key in entry["keys"]]
        if [array_sha256(value) for value in values] != entry["tensor_sha256"]:
            raise ValueError("Initial checkpoint tensor values changed.")
        model.set_weights(values)
        hashes = [array_sha256(value) for value in model.get_weights()]
        if hashes != entry["tensor_sha256"]:
            raise ValueError("Model did not restore the exact initial tensors.")
        result[architecture] = hashes
    return result


def local_training_order(sample_count, seed):
    if sample_count < 1:
        raise ValueError("Client training data must be nonempty.")
    return np.random.default_rng(seed).permutation(sample_count)


def aggregate_models(uploads, sample_counts, rule="fedavg"):
    """Aggregate only accepted compatible models; counts are trusted allocations."""
    if not uploads or len(uploads) != len(sample_counts):
        raise ValueError("Require nonempty uploads and one sample count per upload.")
    counts = np.asarray(sample_counts)
    if (counts.ndim != 1 or not np.issubdtype(counts.dtype, np.integer)
            or np.issubdtype(counts.dtype, np.bool_) or (counts <= 0).any()):
        raise ValueError("Sample counts must be positive integers.")
    if rule not in ("fedavg", "median"):
        raise ValueError("Unsupported aggregation rule.")
    if not uploads[0] or any(len(item) != len(uploads[0]) for item in uploads):
        raise ValueError("Tensor counts differ or models have no tensors.")
    coefficients = counts.astype(np.float64) / counts.astype(np.float64).sum()
    aggregate = []
    for index, reference in enumerate(uploads[0]):
        reference = np.asarray(reference)
        tensors = [np.asarray(item[index]) for item in uploads]
        if not np.issubdtype(reference.dtype, np.floating):
            raise ValueError("Only floating-point model tensors are supported.")
        if any(item.shape != reference.shape or item.dtype != reference.dtype for item in tensors):
            raise ValueError("Incompatible tensor shape or dtype.")
        if any(not np.isfinite(item).all() for item in tensors):
            raise ValueError("Non-finite submitted weights.")
        if rule == "fedavg":
            value = np.zeros(reference.shape, dtype=np.float64)
            for coefficient, tensor in zip(coefficients, tensors):
                value += coefficient * tensor.astype(np.float64)
            value = value.astype(reference.dtype)
        else:
            value = np.median(np.stack(tensors), axis=0).astype(reference.dtype)
        if not np.isfinite(value).all():
            raise FloatingPointError("Non-finite aggregate.")
        aggregate.append(value)
    return aggregate
