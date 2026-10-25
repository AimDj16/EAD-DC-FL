# Matched FedAvg development experiments

FedAvg is the primary aggregation rule for new matched development runs. It is
sample-count weighted within each compatible architecture group. After EAD
filtering, weights are renormalised over accepted clients. Median remains an
explicit `--aggregation median` comparator. Empty accepted sets retain the
pre-round model under the existing failure policy.

## Shared starting conditions

Create the shared inputs once on the UWE environment, from the project root:

```bash
python scripts/prepare_matched_development.py
```

The command performs no training. It saves one initial checkpoint for each of
Small, Medium and Deep, plus a manifest covering the dataset, split and client
allocations, normalisation, master checkpoint, attack protocol/poison-row set,
feature/label definitions through their manifests, model code and shared helper.
It refuses to overwrite an existing experiment directory. Reuse this directory
across all matched conditions; do not recreate initial models per condition.

All 30 registered clients participate in every one of the four development
rounds, with the same order within each architecture. A local NumPy permutation
is derived from the client/round seed; Keras shuffling is disabled. Local epochs,
batch sizes, learning rate and KD budgets are registered and checked. EAD, KD and
attacks may change outcomes, retained contributions and subsequent model states.
Those intended differences are not treated as failures of matching.

The guarantee is identical saved starting tensors for a given architecture
across matched conditions, not identical tensors across different architectures.
This contract is a seed-42, four-round development protocol, not a final
multiple-seed experiment design. It does not certify preprocessing provenance or
full-run deterministic execution. Full participant identity is checked, not
inferred from an equal cohort size. A different partial-participation design
requires a separately registered feasible schedule.

## Running and checking comparisons

The Gaussian, targeted, ablation and multiround runners now default to FedAvg.
For example, repeat the zero-noise check using the new shared initial states:

```bash
python -u scripts/run_gaussian_development_pilot.py --mode original --ead off --kd on --arm benign --sigma 0 --aggregation fedavg
python -u scripts/run_gaussian_development_pilot.py --mode original --ead off --kd on --arm attack --sigma 0 --aggregation fedavg
```

Each output directory begins `matched_fedavg_<experiment ID prefix>_` and retains
the original descriptive suffix. It cannot overwrite an old Median run or an
existing matched run. `--matched-experiment PATH` selects an existing shared
record; the seed, horizon, training settings and input hashes must agree.

All EAD/KD on/off cells use that same record. Label-flipping runs reuse the saved
compromised IDs and poison-row sets; Gaussian runs reuse the compromised IDs and
their isolated client/round noise streams. Attack settings are not data-allocation
settings. The full master data resource is registered even when KD is disabled;
use versus availability is reported by the method condition.

Compare completed reports with:

```bash
python scripts/check_matched_run_inputs.py PATH_TO_FIRST_REPORT PATH_TO_SECOND_REPORT
```

The audit checks initial tensor hashes, data/manifest identity, training budgets,
execution environment, actual participants and exact row-order fingerprints.
It deliberately permits different attacks, screening, teacher/KD decisions and
later weights. Report-input matching does not replace the zero-noise checkpoint
array comparison or statistical replication.

## Interpretation and validation

The new saved initial states and explicit local-order policy define a new matched
development baseline. Previous Median results remain historical references; they
must not be relabelled as FedAvg or mixed into the new matched ablations. An exact
Median/FedAvg ablation requires fresh runs under this shared contract.

Run the numerical and contract checks with:

```bash
python -m unittest discover -s tests -p 'test_matched_experiments.py' -v
```

These tests require NumPy, not TensorFlow. GPU preparation, full TensorFlow runner
execution and same-runner zero-noise equality still require validation on UWE.
Retain all existing data, split, master, validation/test and warm-start policies;
the final test remains outside this development procedure.
