"""Prepare a candidate feature-group split without modifying data or training."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_SHA256 = "54b24fb0405e5f6f03ae2792c65bbd93a98db47e573778d1f4cd3719b6859fbd"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=Path("data/raw/idsiot2024/Process_1 IDS-IoT-2024.csv")
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("configs/data_protocol.json")
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/partitions/idsiot2024/candidate_seed42")
    )
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(
            f"Candidate output already exists: {args.output}. "
            "Use a new --output path."
        )

    cfg = json.loads(args.protocol.read_text(encoding="utf-8-sig"))
    required = {
        "status": "candidate_not_frozen",
        "dataset": "idsiot2024",
        "grouping": "all_feature_columns_excluding_target",
        "duplicate_policy": "retain_rows_keep_groups_together",
        "conflicting_label_policy": "retain_original_labels_keep_groups_together",
        "exact_class_proportions_required": False,
        "all_classes_required_in_each_partition": True,
        "preprocessing_provenance_verified": False,
    }
    for key, value in required.items():
        if cfg.get(key) != value:
            raise ValueError(f"Unsupported protocol value for {key}.")

    names = list(cfg["desired_row_fractions"])
    if names != [
        "client_training", "server_kd", "server_validation", "test"
    ]:
        raise ValueError("Unexpected partition names or ordering.")

    fractions = np.array(
        list(cfg["desired_row_fractions"].values()), dtype=float
    )
    if (
        not np.isfinite(fractions).all()
        or not (fractions > 0).all()
        or not np.isclose(fractions.sum(), 1)
    ):
        raise ValueError("Fractions must be positive and sum to one.")

    source_hash = sha256(args.input)
    if source_hash != EXPECTED_SHA256:
        raise ValueError("Dataset checksum does not match the audited source.")

    df = pd.read_csv(args.input)
    target = cfg["target_column"]
    if target not in df or df.isna().any().any():
        raise ValueError("Missing target column or missing data values.")

    features = [c for c in df if c != target]
    if len(df) != 96280 or len(features) != 96:
        raise ValueError("Unexpected dataset shape.")
    if not all(pd.api.types.is_numeric_dtype(df[c]) for c in features):
        raise ValueError("The audited feature schema must be numeric.")
    if not np.isfinite(df[features].to_numpy()).all():
        raise ValueError("Non-finite feature values.")

    classes = sorted(df[target].unique().tolist())
    if len(classes) != 7:
        raise ValueError("Expected seven classes.")

    group_ids = (
        df.groupby(features, sort=True, dropna=False)
          .ngroup()
          .to_numpy(dtype=np.int64)
    )
    n_groups = int(group_ids.max()) + 1
    group_counts = (
        pd.crosstab(group_ids, df[target])
          .reindex(
              index=np.arange(n_groups),
              columns=classes,
              fill_value=0
          )
          .to_numpy(dtype=np.int64)
    )

    sizes = group_counts.sum(axis=1)
    totals = group_counts.sum(axis=0)
    minimum_groups = int(cfg.get("minimum_feature_groups_per_class_per_partition", 2))
    if minimum_groups < 1:
        raise ValueError("Minimum group coverage must be positive.")
    assigned_groups = np.zeros((len(names), len(classes)), dtype=np.int64)
    remaining = (group_counts > 0).sum(axis=0)

    if (remaining < minimum_groups * len(names)).any():
        raise ValueError(
            "Too few feature groups to cover every class in every partition."
        )

    targets = fractions[:, None] * totals[None, :]
    row_targets = fractions * len(df)
    counts = np.zeros((len(names), len(classes)), dtype=np.int64)
    rows = np.zeros(len(names), dtype=np.int64)
    assignment = np.full(n_groups, -1, dtype=np.int8)

    seed = int(cfg["allocation_seed"])
    order = np.random.default_rng(seed).permutation(n_groups)
    order = order[np.argsort(-sizes[order], kind="stable")]

    for group in order:
        contribution = group_counts[group]
        present = contribution > 0
        remaining -= present

        missing = np.maximum(minimum_groups - assigned_groups, 0).sum(axis=0)
        feasible = np.all(
            missing[None, :]
            - (present[None, :] & (assigned_groups < minimum_groups))
            <= remaining[None, :],
            axis=1
        )

        delta = contribution[None, :] / targets
        error = counts / targets - 1
        row_delta = sizes[group] / row_targets
        row_error = rows / row_targets - 1

        costs = (2 * error * delta + delta**2).sum(axis=1)
        costs += 2 * row_error * row_delta + row_delta**2
        costs[~feasible] = np.inf

        if not np.isfinite(costs).any():
            raise ValueError(
                "Greedy allocation cannot maintain class coverage; "
                "no candidate saved."
            )

        part = int(np.argmin(costs))
        assignment[group] = part
        counts[part] += contribution
        rows[part] += sizes[group]
        assigned_groups[part] += present

    if (assigned_groups < minimum_groups).any():
        raise RuntimeError("Minimum group-coverage verification failed.")
    row_partition = assignment[group_ids]
    if (
        (assignment < 0).any()
        or (counts <= 0).any()
        or rows.sum() != len(df)
    ):
        raise RuntimeError("Allocation verification failed.")

    for part in range(len(names)):
        actual = (
            df.loc[row_partition == part, target]
              .value_counts()
              .reindex(classes, fill_value=0)
              .to_numpy()
        )
        if not np.array_equal(actual, counts[part]):
            raise RuntimeError("Row-index and group-count verification failed.")

    coverage = np.array([
        (group_counts[assignment == p] > 0).sum(axis=0)
        for p in range(len(names))
    ])

    low_group_support = [
        {
            "partition": names[p],
            "class": classes[c],
            "feature_groups": int(coverage[p, c])
        }
        for p in range(len(names))
        for c in range(len(classes))
        if coverage[p, c] < 5
    ]

    args.output.mkdir(parents=True, exist_ok=False)
    indices_path = args.output / "indices.npz"
    indices = {
        name: np.flatnonzero(row_partition == p)
        for p, name in enumerate(names)
    }
    np.savez_compressed(
        indices_path,
        **indices,
        row_group_id=group_ids,
        group_partition=assignment
    )

    manifest = {
        "status": "candidate_not_frozen",
        "training_performed": False,
        "algorithm": "descending_group_size_relative_squared_error_greedy_v2",
        "objective": (
            "equal-weight class-relative squared error "
            "plus total-row relative squared error"
        ),
        "tie_breaking": "seeded group order; fixed partition ordering",
        "source_sha256": source_hash,
        "protocol_sha256": sha256(args.protocol),
        "script_sha256": sha256(Path(__file__)),
        "indices_sha256": sha256(indices_path),
        "protocol": cfg,
        "rows": len(df),
        "feature_names": features,
        "feature_groups": n_groups,
        "classes": classes,
        "partition_order": names,
        "realised_rows": dict(zip(names, map(int, rows))),
        "realised_fractions": dict(
            zip(names, map(float, rows / len(df)))
        ),
        "class_counts": {
            name: dict(zip(classes, map(int, counts[p])))
            for p, name in enumerate(names)
        },
        "class_feature_groups": {
            name: dict(zip(classes, map(int, coverage[p])))
            for p, name in enumerate(names)
        },
        "low_group_support_below_five": low_group_support,
        "checks": {
            "all_rows_assigned_once": True,
            "feature_groups_disjoint": True,
            "all_classes_present": True, "minimum_groups_per_class": minimum_groups, "minimum_group_coverage_met": True
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__
        },
        "limitations": [
            "Greedy candidate, not a globally optimal split.",
            "Class presence does not establish sufficient group support.",
            "Feature-group separation is not capture or temporal separation.",
            "Inherited preprocessing provenance remains unverified."
        ]
    }

    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8"
    )

    print("CLASS COUNTS:")
    print(pd.DataFrame(counts, index=names, columns=classes).to_string())

    print("\nROW ALLOCATION:")
    print(pd.DataFrame({
        "Rows": rows,
        "Desired_fraction": fractions,
        "Realised_fraction": rows / len(df)
    }, index=names).round(6).to_string())

    print("\nCLASS-SUPPORTING FEATURE GROUPS:")
    print(pd.DataFrame(coverage, index=names, columns=classes).to_string())

    print("\nINTEGRITY CHECKS: PASS")
    print("Candidate frozen: NO")
    print("Training performed: NO")
    print(f"Saved: {args.output}")

    if low_group_support:
        print(
            "Low feature-group support is recorded in the manifest; "
            "inspect before acceptance."
        )


if __name__ == "__main__":
    main()
