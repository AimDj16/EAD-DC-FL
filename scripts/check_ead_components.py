import json
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler
from pyod.models.lof import LOF
from pyod.models.iforest import IForest
from pyod.models.knn import KNN
from pyod.models.pca import PCA
from pyod.models.ocsvm import OCSVM


SEED = 42
INITIAL_CONTAMINATION = 0.20
CALIBRATION_INCREMENT = 0.10
MAX_CONTAMINATION = 0.40
COUNT_RANGE_THRESHOLD = 0

rng = np.random.default_rng(SEED)

# Small synthetic vectors for component checks.
# Full flattened model weights will require a separate integration check.
vectors = rng.normal(size=(10, 8))
vectors[-2:] += 5.0
scaled_vectors = StandardScaler().fit_transform(vectors)

ensembles = {
    "three_detectors": ["LOF", "IForest", "KNN"],
    "five_detectors": ["LOF", "IForest", "KNN", "PCA", "OCSVM"],
}


def fit_detectors(contamination):
    detectors = {
        "LOF": LOF(n_neighbors=5, contamination=contamination),
        "IForest": IForest(
            contamination=contamination,
            random_state=SEED,
        ),
        "KNN": KNN(n_neighbors=5, contamination=contamination),
        "PCA": PCA(
            contamination=contamination,
            random_state=SEED,
        ),
        "OCSVM": OCSVM(contamination=contamination),
    }

    records = {}
    for name, detector in detectors.items():
        detector.fit(scaled_vectors)
        scores = np.asarray(detector.decision_scores_, dtype=float)
        flags = np.asarray(detector.labels_, dtype=int)
        threshold = float(detector.threshold_)

        assert scores.shape == (10,), name
        assert flags.shape == (10,), name
        assert np.isfinite(scores).all(), name
        assert np.isfinite(threshold), name
        assert np.isin(flags, [0, 1]).all(), name

        records[name] = {
            "scores": scores.tolist(),
            "flags": flags.tolist(),
            "threshold": threshold,
            "flagged_count": int(flags.sum()),
        }
    return records


def vote(flag_matrix):
    flag_matrix = np.asarray(flag_matrix, dtype=int)
    assert flag_matrix.ndim == 2
    assert np.isin(flag_matrix, [0, 1]).all()
    detector_count = flag_matrix.shape[1]
    totals = flag_matrix.sum(axis=1)
    return {
        "vote_counts": totals,
        "majority": totals >= (detector_count // 2 + 1),
        "strict": totals == detector_count,
    }


def calibration_decision(flag_matrix, contamination):
    # Count disagreement, not disagreement about client identities.
    counts = np.asarray(flag_matrix, dtype=int).sum(axis=0)
    count_range = int(counts.max() - counts.min())
    next_contamination = min(
        MAX_CONTAMINATION,
        round(contamination + CALIBRATION_INCREMENT, 10),
    )
    rerun = (
        count_range > COUNT_RANGE_THRESHOLD
        and next_contamination > contamination
    )
    return {
        "flagged_counts": counts.tolist(),
        "count_range": count_range,
        "rerun": bool(rerun),
        "contamination": (
            next_contamination if rerun else contamination
        ),
    }


def filtered_median(updates, rejected, previous):
    accepted = updates[~np.asarray(rejected, dtype=bool)]
    if len(accepted) == 0:
        return previous.copy(), True
    return np.median(accepted, axis=0), False


# Deterministic voting checks.
manual_three = np.array([
    [0, 0, 0],
    [1, 0, 0],
    [1, 1, 0],
    [1, 1, 1],
])
result = vote(manual_three)
assert result["majority"].tolist() == [False, False, True, True]
assert result["strict"].tolist() == [False, False, False, True]

manual_five = np.array([
    [1, 1, 0, 0, 0],
    [1, 1, 1, 0, 0],
    [1, 1, 1, 1, 1],
])
result = vote(manual_five)
assert result["majority"].tolist() == [False, True, True]
assert result["strict"].tolist() == [False, False, True]

# Equal counts can hide disagreement about which client is flagged.
equal_counts = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
assert not calibration_decision(equal_counts, 0.20)["rerun"]

unequal_counts = np.array([[1, 1, 0], [1, 0, 0], [0, 0, 0]])
decision = calibration_decision(unequal_counts, 0.20)
assert decision["rerun"]
assert decision["contamination"] == 0.30
assert not calibration_decision(unequal_counts, 0.40)["rerun"]

initial_records = fit_detectors(INITIAL_CONTAMINATION)
ensemble_reports = {}

for ensemble_name, names in ensembles.items():
    initial_flags = np.column_stack([
        initial_records[name]["flags"] for name in names
    ])
    calibration = calibration_decision(
        initial_flags, INITIAL_CONTAMINATION
    )

    # One calibration rerun for this component check.
    final_records = (
        fit_detectors(calibration["contamination"])
        if calibration["rerun"]
        else initial_records
    )
    final_flags = np.column_stack([
        final_records[name]["flags"] for name in names
    ])
    voting = vote(final_flags)
    assert np.all(~voting["strict"] | voting["majority"])

    aggregation = {}
    previous = np.zeros(vectors.shape[1])
    for rule in ("majority", "strict"):
        rejected = voting[rule]
        aggregate, fallback = filtered_median(
            vectors, rejected, previous
        )
        assert aggregate.shape == previous.shape
        assert np.isfinite(aggregate).all()
        aggregation[rule] = {
            "rejected_indices": np.flatnonzero(rejected).tolist(),
            "accepted_count": int((~rejected).sum()),
            "retained_previous": bool(fallback),
            "aggregate": aggregate.tolist(),
        }

    ensemble_reports[ensemble_name] = {
        "active_detectors": names,
        "calibration": calibration,
        "final_detectors": {
            name: final_records[name] for name in names
        },
        "vote_counts": voting["vote_counts"].tolist(),
        "aggregation": aggregation,
    }

    print(
        f"{ensemble_name}: "
        f"calibration_rerun={calibration['rerun']}, "
        f"contamination={calibration['contamination']:.2f}, "
        f"majority_rejected={int(voting['majority'].sum())}, "
        f"strict_rejected={int(voting['strict'].sum())}"
    )

# Verify coordinate-wise Median and the empty-accepted-set policy.
example = np.array([[1., 9.], [3., 5.], [100., -100.]])
aggregate, fallback = filtered_median(
    example, [False, False, True], np.array([7., 8.])
)
assert np.array_equal(aggregate, [2., 7.])
assert not fallback

previous = np.array([7., 8.])
aggregate, fallback = filtered_median(
    example, [True, True, True], previous
)
assert np.array_equal(aggregate, previous)
assert fallback

report = {
    "status": "pass",
    "seed": SEED,
    "synthetic_shape": list(vectors.shape),
    "initial_detectors": initial_records,
    "ensembles": ensemble_reports,
    "checks": {
        "finite_detector_scores": True,
        "binary_detector_labels": True,
        "majority_and_strict_voting": True,
        "calibration_trigger_and_cap": True,
        "coordinate_wise_median": True,
        "empty_accepted_set_retains_previous": True,
    },
    "real_dataset_training_performed": False,
    "federated_training_performed": False,
    "primary_ensemble_frozen": False,
    "full_model_weight_screening_verified": False,
}

output = Path("outputs/checks/ead_components_smoke/report.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("Detector, voting and calibration checks: PASS")
print("Median and empty-accepted-set checks: PASS")
print("EAD COMPONENT CHECKS: PASS")
print(f"Saved: {output}")
