"""Capacity-constrained Dirichlet-derived label skew and protocol checks.

IPF balances positive class/client preferences to fixed integer margins. Residual
bipartite flow rounds the target to floor/ceiling cells with exact margins. This
is a controlled allocation design, not an unconstrained Dirichlet partition.
"""
from collections import deque
import hashlib
import math
from pathlib import Path
import tarfile

import numpy as np

from .matched_experiments import array_sha256, canonical_sha256, file_sha256, load_matched_experiment


ARCHITECTURES = ("small", "medium", "deep")
TRAINING_SETTINGS = {
    "local_epochs": 1, "local_batch_size": 128, "learning_rate": 0.001,
    "kd_epochs": 3, "kd_batch_size": 256, "kd_temperature": 3.0,
    "warm_start_rounds": 3,
}
ALLOCATION_VERSION = "within_architecture_dirichlet_ipf_flow_v1"


def balanced_class_counts(class_counts, capacities, alpha, seed):
    """Draw preferences once, balance and round without dropping or retrying data."""
    row = np.asarray(class_counts)
    col = np.asarray(capacities)
    if (row.ndim != 1 or col.ndim != 1 or not len(row) or not len(col)
            or row.dtype.kind not in "iu" or col.dtype.kind not in "iu"
            or (row < 0).any() or (col <= 0).any()
            or row.sum() != col.sum() or not np.isfinite(alpha) or alpha <= 0):
        raise ValueError("Require non-negative integer class counts, positive capacities, equal totals and finite positive alpha.")
    active = np.flatnonzero(row)
    rng = np.random.default_rng(seed)
    preference = rng.dirichlet(np.full(len(col), alpha), size=len(active))
    # Prevent floating underflow becoming a structural zero in the IPF support.
    target = np.maximum(preference, 1e-100) * row[active, None]
    tolerance = 1e-8
    for iterations in range(1, 10001):
        target *= (row[active] / target.sum(axis=1))[:, None]
        target *= (col / target.sum(axis=0))[None, :]
        if np.max(np.abs(target.sum(axis=1) - row[active])) <= tolerance:
            break
    else:
        raise ValueError("IPF did not converge; allocation preserved for review, no automatic redraw.")
    if not np.isfinite(target).all():
        raise ValueError("Non-finite balanced allocation targets.")
    counts = np.floor(target).astype(np.int64)
    need_row = row[active] - counts.sum(axis=1)
    need_col = col - counts.sum(axis=0)
    if (need_row < 0).any() or (need_col < 0).any() or need_row.sum() != need_col.sum():
        raise ValueError("Numerical rounding margins are infeasible.")
    nr, nc = target.shape
    source, sink = nr + nc, nr + nc + 1
    residual = np.zeros((sink + 1, sink + 1), dtype=np.int64)
    residual[source, :nr] = need_row
    residual[nr:nr + nc, sink] = need_col
    # Prefer the larger fractional remainders; augmenting paths retain feasibility.
    fractions = target - counts
    available = (fractions > 0).astype(np.int64)
    residual[:nr, nr:nr + nc] = available
    neighbours = {}
    neighbours[source] = list(range(nr))
    for i in range(nr):
        neighbours[i] = [nr + int(j) for j in np.argsort(-fractions[i], kind="stable")] + [source]
    for j in range(nc):
        neighbours[nr + j] = [sink] + list(range(nr))
    neighbours[sink] = []
    for _ in range(int(need_row.sum())):
        parent = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for child in neighbours[node]:
                if residual[node, child] > 0 and child not in parent:
                    parent[child] = node
                    queue.append(child)
        if sink not in parent:
            raise ValueError("Residual allocation flow is infeasible; no data were reassigned.")
        node = sink
        while parent[node] is not None:
            previous = parent[node]
            residual[previous, node] -= 1
            residual[node, previous] += 1
            node = previous
    counts += available - residual[:nr, nr:nr + nc]
    output = np.zeros((len(row), len(col)), dtype=np.int64)
    output[active] = counts
    if not (np.array_equal(output.sum(axis=1), row)
            and np.array_equal(output.sum(axis=0), col)
            and np.all(counts >= np.floor(target)) and np.all(counts <= np.ceil(target))):
        raise ValueError("Rounded allocation did not preserve margins.")
    return output, {
        "ipf_iterations": iterations, "ipf_tolerance": tolerance,
        "max_margin_error_before_rounding": float(np.max(np.abs(target.sum(axis=1) - row[active]))),
        "class_counts": row.tolist(), "client_capacities": col.tolist(),
        "integer_class_client_counts": output.tolist(),
    }


def class_distribution_metrics(client_counts):
    values = np.asarray(client_counts, dtype=np.float64)
    if values.ndim != 2 or (values < 0).any() or (values.sum(axis=1) <= 0).any():
        raise ValueError("Each client needs a nonempty class-count vector.")
    reference = values.sum(axis=0) / values.sum()
    proportions = values / values.sum(axis=1, keepdims=True)
    tv = 0.5 * np.abs(proportions - reference).sum(axis=1)
    js = []
    for p in proportions:
        midpoint = (p + reference) / 2
        def divergence(a):
            mask = a > 0
            return float(np.sum(a[mask] * np.log2(a[mask] / midpoint[mask])))
        js.append((divergence(p) + divergence(reference)) / 2)
    return {
        "group_class_proportions": reference.tolist(),
        "client_class_proportions": proportions.tolist(),
        "client_total_variation": tv.tolist(), "mean_total_variation": float(tv.mean()),
        "client_js_divergence_bits": js, "mean_js_divergence_bits": float(np.mean(js)),
        "client_classes_present": (values > 0).sum(axis=1).astype(int).tolist(),
    }


def make_allocation(original, labels, members_by_architecture, class_count, alpha=0.5, seed=42):
    """Only labels for original training-row IDs are accessed."""
    output, reports = {}, {}
    all_members = [cid for ids in members_by_architecture.values() for cid in ids]
    if len(set(all_members)) != len(all_members) or set(original) != {f"client_{cid:02d}" for cid in all_members}:
        raise ValueError("Architecture groups must cover distinct registered clients exactly.")
    for index, (architecture, ids) in enumerate(members_by_architecture.items()):
        keys = [f"client_{cid:02d}" for cid in ids]
        pool = np.concatenate([original[key] for key in keys])
        if len(np.unique(pool)) != len(pool):
            raise ValueError("Original architecture pool contains duplicate row IDs.")
        y = labels[pool]
        if (y < 0).any() or (y >= class_count).any():
            raise ValueError("Invalid training labels.")
        capacities = np.array([len(original[key]) for key in keys], dtype=np.int64)
        class_counts = np.bincount(y, minlength=class_count)
        counts, balancing = balanced_class_counts(class_counts, capacities, alpha,
                                                 np.random.SeedSequence([seed, index, 101]))
        shuffled = [[] for _ in ids]
        for label in range(class_count):
            rows = pool[y == label].copy()
            np.random.default_rng(np.random.SeedSequence([seed, index, label, 202])).shuffle(rows)
            boundaries = np.cumsum(counts[label])[:-1]
            for j, part in enumerate(np.split(rows, boundaries)):
                shuffled[j].extend(part.tolist())
        for j, key in enumerate(keys):
            rows = np.asarray(shuffled[j], dtype=np.int64)
            np.random.default_rng(np.random.SeedSequence([seed, index, j, 303])).shuffle(rows)
            output[key] = rows
        previous_counts = [np.bincount(labels[original[key]], minlength=class_count) for key in keys]
        reports[architecture] = {
            "client_ids": list(ids), "balancing": balancing,
            "iid": class_distribution_metrics(previous_counts),
            "labelskew": class_distribution_metrics(counts.T),
        }
    verify_allocation(original, output, labels, members_by_architecture, class_count)
    return output, reports


def verify_allocation(original, changed, labels, members_by_architecture, class_count):
    if set(original) != set(changed):
        raise ValueError("Client identities changed.")
    before = np.concatenate(list(original.values()))
    after = np.concatenate(list(changed.values()))
    if (len(np.unique(after)) != len(after) or len(np.unique(before)) != len(before)
            or not np.array_equal(np.sort(before), np.sort(after))):
        raise ValueError("Allocation must cover each original training row exactly once.")
    for key in original:
        if len(original[key]) != len(changed[key]):
            raise ValueError("Client sample capacity changed: " + key)
    for ids in members_by_architecture.values():
        left = np.concatenate([original[f"client_{cid:02d}"] for cid in ids])
        right = np.concatenate([changed[f"client_{cid:02d}"] for cid in ids])
        if not np.array_equal(np.sort(left), np.sort(right)):
            raise ValueError("Architecture training pool changed.")
        if not np.array_equal(np.bincount(labels[left], minlength=class_count),
                              np.bincount(labels[right], minlength=class_count)):
            raise ValueError("Architecture class totals changed.")


def poison_opportunities(allocations, labels, malicious_ids, source_id):
    """Zero opportunity is permitted per client; attacker identities never move."""
    return {f"client_{cid:02d}": allocations[f"client_{cid:02d}"][
                labels[allocations[f"client_{cid:02d}"]] == source_id].copy()
            for cid in malicious_ids}


def verify_subset_record(current, reference, location="record"):
    """Compare every original field, allowing additional diagnostic fields only."""
    if isinstance(reference, dict):
        if not isinstance(current, dict) or not set(reference).issubset(current):
            raise ValueError("Replay fields differ at " + location)
        for key, value in reference.items():
            verify_subset_record(current[key], value, location + "/" + str(key))
    elif isinstance(reference, list):
        if not isinstance(current, list) or len(current) != len(reference):
            raise ValueError("Replay list differs at " + location)
        for index, (a, b) in enumerate(zip(current, reference)):
            verify_subset_record(a, b, location + "/" + str(index))
    elif current != reference:
        raise ValueError("Replay differs at " + location)


def run_directory(manifest, arm, ead, kd):
    return Path("outputs/development") / (
        f"matched_fedavg_{manifest['experiment_id'][:12]}_labelskew_a0p5_alloc42_"
        f"{arm}_original_ead_{ead}_kd_{kd}_seed{manifest['seed']}_rounds12_v1"
    )


def iid_reference_directory(base, arm, ead, kd):
    attack = "gaussian" if arm == "benign" else "targeted"
    return Path("outputs/development") / (
        f"matched_fedavg_{base['experiment_id'][:12]}_replication_predict3_"
        f"{attack}_sigma0p0_{arm}_original_ead_{ead}_kd_{kd}_"
        f"seed{base['seed']}_rounds12"
    )


def check_metric_counts(value):
    matrix = np.asarray(value["confusion_matrix"])
    names = value["confusion_class_order"]
    if matrix.shape != (len(names), len(names)) or matrix.dtype.kind not in "iu" or (matrix < 0).any():
        raise ValueError("Invalid confusion matrix.")
    count = int(matrix.sum())
    support = matrix.sum(axis=1)
    if count != 7600 or (support <= 0).any():
        raise ValueError("Expected the fixed all-class development validation partition.")
    tp = np.diag(matrix)
    denominator = support + matrix.sum(axis=0)
    f1 = np.divide(2*tp, denominator, out=np.zeros(len(names), dtype=float), where=denominator != 0)
    source, target = names.index("Malware"), names.index("Normal")
    expected = {
        "accuracy": float(tp.sum()/count), "macro_f1": float(f1.mean()),
        "targeted_hits": int(matrix[source, target]), "targeted_source_rows": int(support[source]),
        "targeted_misclassification_rate": float(matrix[source, target]/support[source]),
        "normal_false_alarm_rate": float(1-matrix[target, target]/support[target]),
    }
    if count != 7600 or support[source] != 801:
        raise ValueError("Unexpected validation support for this fixed-partition protocol.")
    for key, number in expected.items():
        if not math.isclose(value[key], number, abs_tol=1e-12, rel_tol=1e-12):
            raise ValueError("Metric does not match confusion counts: " + key)
    for j, name in enumerate(names):
        if value["class_support"][name] != int(support[j]):
            raise ValueError("Class support differs from counts.")
        if not math.isclose(value["per_class_recall"][name], tp[j]/support[j], abs_tol=1e-12):
            raise ValueError("Class recall differs from counts.")


def validate_completed_run(report, manifest, arm, ead, kd, selection):
    expected = {
        "status": "completed", "configuration_id": "matched_labelskew_development_v1",
        "data_regime": "labelskew", "scientific_run_count": 1,
        "seed": manifest["seed"], "planned_rounds": 12, "contract_rounds": 12,
        "matched_experiment_id": manifest["experiment_id"], "mode": "original",
        "ead_enabled": ead == "on", "kd_enabled": kd == "on", "arm": arm,
        "aggregation": "sample_weighted_fedavg", "training_settings": TRAINING_SETTINGS,
        "allocation_version": ALLOCATION_VERSION, "allocation_seed": 42, "dirichlet_alpha": 0.5,
        "initial_state_sha256": {name: entry["tensor_sha256"] for name, entry in manifest["initial_models"].items()},
        "client_manifest_sha256": manifest["input_sha256"][manifest["client_manifest"]],
        "source_sha256": manifest["input_sha256"]["data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv"],
        "master_weights_sha256": manifest["input_sha256"]["outputs/development/master_pretrain_seed42/master_weights.npz"],
        "models_and_kd_sha256": manifest["input_sha256"]["src/ead_dc_fl/models_and_kd.py"],
        "attack_operator_sha256": manifest["input_sha256"]["src/ead_dc_fl/attacks.py"],
        "script_sha256": manifest["input_sha256"]["scripts/run_labelskew_development.py"],
        "label_skew_module_sha256": manifest["input_sha256"]["src/ead_dc_fl/label_skew.py"],
        "test_evaluated": False, "final_protocol_frozen": False, "preprocessing_provenance_verified": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError("Label-skew result differs: " + key)
    if [r["round"] for r in report.get("rounds", [])] != list(range(1, 13)):
        raise ValueError("Label-skew rounds are incomplete or unordered.")
    opportunity = {c["client_id"]: c["poisoned_rows"] for c in selection["clients"]}
    compromised_ids = set(selection["malicious_client_ids"])
    for record in report["rounds"]:
        if record["participation"] != manifest["participation"][str(record["round"])]:
            raise ValueError("Label-skew participants changed.")
        if kd == "on" and record["round"] <= 3:
            if record["teacher"] != "master":
                raise ValueError("Original master warm-start was changed.")
        else:
            eligible = [name for name in ARCHITECTURES if not record["clusters"][name]["retained_previous_model"]]
            teacher = max(eligible, key=lambda name: record["clusters"][name]["pre_kd_validation"]["accuracy"]) if eligible else None
            if record["teacher"] != teacher:
                raise ValueError("Adaptive teacher or tie-breaking changed.")
        for name, cluster in record["clusters"].items():
            cohort = set(cluster["client_ids"])
            rejected = set(cluster["rejected_client_ids"])
            designated = (cohort & compromised_ids) if arm == "attack" else set()
            effective = {cid for cid in designated if opportunity[cid] > 0}
            for upload in cluster["upload_diagnostics"]:
                cid = upload["client_id"]
                if (upload["designated_malicious_client"] != (cid in designated)
                        or upload["poisoning_applied"] != (cid in effective)
                        or upload["poisoned_label_rows"] != (opportunity[cid] if cid in designated else 0)):
                    raise ValueError("Poison execution differs from registered opportunities.")
                if cid in compromised_ids and upload["source_class_rows_available"] != opportunity[cid]:
                    raise ValueError("Compromised client's source-class opportunity changed.")
                if (upload["training_labels_original_sha256"] == upload["training_labels_used_sha256"]) != (cid not in effective):
                    raise ValueError("Label hashes disagree with actual poisoning status.")
            audit = cluster["screening_audit"]
            if (set(audit["malicious_rejected"]) != designated & rejected
                    or set(audit["malicious_accepted"]) != designated - rejected
                    or set(audit["benign_rejected"]) != rejected - designated):
                raise ValueError("Designated-client screening counts are inconsistent.")
            effect = cluster["effective_poisoning_screening_audit"]
            if (set(effect["effective_poisoned_client_ids"]) != effective
                    or set(effect["effective_poisoned_rejected"]) != effective & rejected
                    or set(effect["effective_poisoned_accepted"]) != effective - rejected
                    or set(effect["designated_zero_opportunity_client_ids"]) != designated - effective):
                raise ValueError("Effective-poison screening counts are inconsistent.")
            if effect["total_poisoned_label_rows"] != sum(opportunity[cid] for cid in designated):
                raise ValueError("Per-group poison-row total changed.")
            if ead == "on":
                votes = [sum(x) for x in zip(*(d["flags"] for d in cluster["final_detection"].values()))]
                initial = [sum(d["flags"]) for d in cluster["initial_detection"].values()]
                if initial != cluster["initial_detector_flagged_counts"] or votes != cluster["vote_counts"]:
                    raise ValueError("Detector count or voting record differs.")
                if rejected != {cid for cid, count in zip(cluster["client_ids"], votes) if count == 3}:
                    raise ValueError("Strict voting differs from rejection mask.")
                trigger = max(initial) != min(initial)
                if cluster["calibration_rerun"] != trigger or cluster["final_contamination"] != (0.3 if trigger else 0.2):
                    raise ValueError("Calibration differs from registered rule.")
            elif rejected:
                raise ValueError("EAD-off run rejected clients.")
            counts = {str(cid): manifest["client_sample_counts"][f"client_{cid:02d}"] for cid in cohort - rejected}
            if counts != cluster["accepted_sample_counts"] or len(counts) != cluster["accepted_count"]:
                raise ValueError("FedAvg sample counts changed.")
            if counts and any(not math.isclose(cluster["fedavg_coefficients"][cid], n/sum(counts.values()), abs_tol=1e-14)
                              for cid, n in counts.items()):
                raise ValueError("FedAvg coefficients are not renormalised survivor counts.")
            pre, post, decision = cluster["pre_kd_validation"], cluster["post_kd_validation"], cluster["kd"]
            check_metric_counts(pre)
            check_metric_counts(post)
            skip = ("kd_disabled" if kd == "off" else
                    "no_accepted_uploads" if cluster["retained_previous_model"] else
                    "no_eligible_teacher" if record["teacher"] is None else
                    "teacher_self_distillation" if name == record["teacher"] else None)
            if skip:
                if decision != {"performed": False, "reason": skip}:
                    raise ValueError("KD skip reason differs from original policy.")
            elif not decision["performed"]:
                raise ValueError("An eligible scheduled KD phase was skipped.")
            if decision["performed"]:
                if kd != "on":
                    raise ValueError("KD was performed in a KD-off run.")
                candidate = decision["candidate_validation"]
                check_metric_counts(candidate)
                accepted = record["round"] <= 3 or candidate["accuracy"] >= pre["accuracy"]
                if decision["accepted"] != accepted or post != (candidate if accepted else pre):
                    raise ValueError("KD commitment differs from original policy.")
            elif pre != post:
                raise ValueError("Skipped KD changed recorded metrics.")


def verify_labelskew_contract(directory, seed, rounds):
    manifest = load_matched_experiment(directory, seed, rounds, TRAINING_SETTINGS)
    if (manifest.get("data_regime") != "labelskew"
            or manifest.get("allocation_version") != ALLOCATION_VERSION
            or manifest.get("allocation_seed") != 42 or manifest.get("dirichlet_alpha") != 0.5):
        raise ValueError("This programme requires the registered alpha0.5/allocation42 label-skew contract.")
    if manifest["client_sample_counts"] != manifest["base_client_sample_counts"]:
        raise ValueError("Client capacities differ from the original IID contract.")
    if manifest["initial_models"] != manifest["base_initial_models"]:
        raise ValueError("Initial checkpoint metadata differs from the IID contract.")
    return manifest


def ids_metrics(labels, predictions, class_names):
    """Additional diagnostic counts; no change to training, teacher or guard."""
    labels, predictions = np.asarray(labels), np.asarray(predictions)
    n = len(class_names)
    if (labels.shape != predictions.shape or labels.ndim != 1 or not len(labels)
            or labels.dtype.kind not in "iu" or predictions.dtype.kind not in "iu"
            or (labels < 0).any() or (labels >= n).any()
            or (predictions < 0).any() or (predictions >= n).any()):
        raise ValueError("Require nonempty valid integer label/prediction vectors.")
    confusion = np.zeros((n, n), dtype=np.int64)
    np.add.at(confusion, (labels, predictions), 1)
    normal = class_names.index("Normal")
    support = confusion.sum(axis=1)
    if support[normal] == 0:
        raise ValueError("Normal false alarm rate requires Normal reference rows.")
    return {"confusion_matrix": confusion.tolist(), "confusion_class_order": list(class_names),
            "class_support": {name: int(support[j]) for j, name in enumerate(class_names)},
            "normal_false_alarm_rate": float(1 - confusion[normal, normal] / support[normal])}


def archive_reports(path, files):
    """Portable aggregate bundle, no raw data/checkpoints; conflicting archives stop."""
    names = {p.as_posix(): p for p in files}
    if len(names) != len(files):
        raise ValueError("Archive paths must be unique.")
    if path.exists():
        with tarfile.open(path, "r:gz") as archive:
            members = [m for m in archive.getmembers() if m.isfile()]
            if (len(members) != len(names) or {m.name for m in members} != set(names)
                    or any(hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                           != file_sha256(names[m.name]) for m in members)):
                raise FileExistsError("Different existing archive preserved: " + str(path))
        return
    temporary = path.with_suffix(path.suffix + ".partial")
    with tarfile.open(temporary, "w:gz") as archive:
        for name in sorted(names):
            archive.add(names[name], arcname=name, recursive=False)
    temporary.replace(path)
